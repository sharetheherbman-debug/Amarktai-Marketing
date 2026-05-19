import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertCircle, ArrowLeft, Building2, CheckCircle2, Loader2, Sparkles } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { webAppApi } from '@/lib/api';
import type { WebApp } from '@/types';

interface FormState {
  name: string;
  url: string;
  description: string;
  category: string;
  targetAudience: string;
}

export default function NewBusinessPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState<FormState>({
    name: '',
    url: '',
    description: '',
    category: '',
    targetAudience: '',
  });
  const [errors, setErrors] = useState<Partial<Record<keyof FormState | 'form', string>>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createdBusiness, setCreatedBusiness] = useState<WebApp | null>(null);

  const intelligence = useMemo(
    () => ((createdBusiness?.scrapedData as Record<string, unknown> | null | undefined) ?? null),
    [createdBusiness]
  );

  useEffect(() => {
    if (!createdBusiness) return;
    const timer = window.setTimeout(() => navigate(`/dashboard/businesses/${createdBusiness.id}`), 1800);
    return () => window.clearTimeout(timer);
  }, [createdBusiness, navigate]);

  const validate = () => {
    const nextErrors: Partial<Record<keyof FormState | 'form', string>> = {};
    if (!form.name.trim() && !form.url.trim()) {
      nextErrors.form = 'Enter at least a business name or a website URL.';
    }
    if (form.url.trim() && !/^([a-z]+:\/\/)?[\w.-]+(?:\.[\w.-]+)+.*$/i.test(form.url.trim())) {
      nextErrors.url = 'Enter a valid website URL or bare domain.';
    }
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);
    try {
      const business = await webAppApi.create({
        name: form.name.trim(),
        url: form.url.trim(),
        description: form.description.trim(),
        category: form.category.trim(),
        targetAudience: form.targetAudience.trim(),
        keyFeatures: [],
        isActive: true,
      });
      setCreatedBusiness(business);
    } catch (error) {
      setErrors({ form: error instanceof Error ? error.message : 'Failed to create business.' });
      setIsSubmitting(false);
    }
  };

  const warnings = ((intelligence?.warnings as string[] | undefined) ?? []).filter(Boolean);
  const scrapeFailed = String(intelligence?.scrape_status || '') === 'failed';

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Link to="/dashboard/businesses" className="inline-flex items-center gap-2 text-sm text-slate-300 hover:text-white">
        <ArrowLeft className="h-4 w-4" />
        Back to Businesses
      </Link>

      <Card className="border-[#252A3A] bg-[#0D0F14]">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-white">
            <Building2 className="h-5 w-5 text-blue-300" />
            Add Business
          </CardTitle>
          <CardDescription>Use a business name only, a website URL only, or both. Description, category, and audience are optional.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {isSubmitting ? (
            <div className="rounded-2xl border border-blue-500/30 bg-blue-500/10 p-4 text-blue-100">
              <div className="flex items-center gap-3 font-medium">
                <Loader2 className="h-5 w-5 animate-spin" />
                Creating business and analyzing website…
              </div>
              <p className="mt-2 text-sm text-blue-100/80">If a website is provided, the scraper runs automatically. If it fails, the business still gets created.</p>
            </div>
          ) : null}

          {createdBusiness ? (
            <div className={`rounded-2xl border p-5 ${scrapeFailed ? 'border-amber-500/30 bg-amber-500/10' : 'border-emerald-500/30 bg-emerald-500/10'}`}>
              <div className="flex items-center gap-3 text-white">
                {scrapeFailed ? <AlertCircle className="h-5 w-5 text-amber-300" /> : <CheckCircle2 className="h-5 w-5 text-emerald-300" />}
                <div>
                  <p className="font-semibold">{scrapeFailed ? 'Business created with analysis warnings' : 'Business created and analyzed'}</p>
                  <p className="text-sm text-slate-300">Redirecting to the business detail page…</p>
                </div>
              </div>

              {scrapeFailed ? (
                <p className="mt-4 text-sm text-amber-100">Website analysis failed, but the business profile was created. Add a description or try refresh.</p>
              ) : null}

              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <div className="rounded-xl border border-white/10 bg-black/10 p-3">
                  <p className="text-xs uppercase tracking-wide text-slate-400">Summary</p>
                  <p className="mt-2 text-sm text-white">{String(intelligence?.page_summary || createdBusiness.description || 'No summary extracted yet.')}</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-black/10 p-3">
                  <p className="text-xs uppercase tracking-wide text-slate-400">Audience</p>
                  <p className="mt-2 text-sm text-white">{String(intelligence?.target_audience_guess || createdBusiness.targetAudience || 'No audience extracted yet.')}</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-black/10 p-3">
                  <p className="text-xs uppercase tracking-wide text-slate-400">Services</p>
                  <p className="mt-2 text-sm text-white">{((intelligence?.products_services as string[] | undefined) ?? []).join(', ') || 'No services extracted yet.'}</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-black/10 p-3">
                  <p className="text-xs uppercase tracking-wide text-slate-400">CTAs / Keywords</p>
                  <p className="mt-2 text-sm text-white">
                    {[
                      ...(((intelligence?.ctas as string[] | undefined) ?? []).slice(0, 3)),
                      ...(((intelligence?.keywords as string[] | undefined) ?? []).slice(0, 3)),
                    ].join(', ') || 'No CTAs or keywords extracted yet.'}
                  </p>
                </div>
              </div>

              {warnings.length > 0 ? (
                <ul className="mt-4 list-disc space-y-1 pl-5 text-xs text-slate-200">
                  {warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}

          {errors.form ? (
            <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">{errors.form}</div>
          ) : null}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="grid gap-5 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="name" className="text-slate-200">Business name</Label>
                <Input
                  id="name"
                  value={form.name}
                  onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                  placeholder="Acme Bakery"
                  className="border-[#252A3A] bg-[#141720] text-white"
                  disabled={isSubmitting || Boolean(createdBusiness)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="url" className="text-slate-200">Website URL</Label>
                <Input
                  id="url"
                  value={form.url}
                  onChange={(event) => setForm((current) => ({ ...current, url: event.target.value }))}
                  placeholder="acmebakery.com"
                  className="border-[#252A3A] bg-[#141720] text-white"
                  disabled={isSubmitting || Boolean(createdBusiness)}
                />
                {errors.url ? <p className="text-xs text-red-300">{errors.url}</p> : <p className="text-xs text-slate-500">Bare domains are normalized to https:// automatically.</p>}
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="description" className="text-slate-200">Short description</Label>
              <Textarea
                id="description"
                value={form.description}
                onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
                placeholder="Optional context about the business, offer, or differentiators"
                className="min-h-[110px] border-[#252A3A] bg-[#141720] text-white"
                disabled={isSubmitting || Boolean(createdBusiness)}
              />
            </div>

            <div className="grid gap-5 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="category" className="text-slate-200">Category</Label>
                <Input
                  id="category"
                  value={form.category}
                  onChange={(event) => setForm((current) => ({ ...current, category: event.target.value }))}
                  placeholder="Retail, SaaS, Services"
                  className="border-[#252A3A] bg-[#141720] text-white"
                  disabled={isSubmitting || Boolean(createdBusiness)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="targetAudience" className="text-slate-200">Target audience</Label>
                <Input
                  id="targetAudience"
                  value={form.targetAudience}
                  onChange={(event) => setForm((current) => ({ ...current, targetAudience: event.target.value }))}
                  placeholder="Local shoppers, B2B buyers, founders"
                  className="border-[#252A3A] bg-[#141720] text-white"
                  disabled={isSubmitting || Boolean(createdBusiness)}
                />
              </div>
            </div>

            <div className="flex flex-wrap justify-end gap-3">
              <Link to="/dashboard/businesses">
                <Button type="button" variant="outline" className="border-[#252A3A] bg-transparent text-slate-200 hover:bg-white/5">
                  Cancel
                </Button>
              </Link>
              <Button type="submit" disabled={isSubmitting || Boolean(createdBusiness)} className="bg-blue-600 hover:bg-blue-500">
                <Sparkles className="mr-2 h-4 w-4" />
                Add Business
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
