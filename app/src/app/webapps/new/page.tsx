import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Plus, X, Globe, Loader2, CheckCircle2, Sparkles } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { webAppApi } from '@/lib/api';
import { toast } from 'sonner';

const categories = [
  'SaaS', 'E-commerce', 'Developer Tools', 'Productivity',
  'Finance', 'Health & Fitness', 'Education', 'Entertainment', 'Other',
];

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show: (i: number) => ({ opacity: 1, y: 0, transition: { delay: i * 0.06 } }),
};

type StepState = 'idle' | 'creating' | 'scraping' | 'done';

export default function NewWebAppPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState<StepState>('idle');
  const [formData, setFormData] = useState({
    name: '',
    url: '',
    description: '',
    category: '',
    targetAudience: '',
    keyFeatures: [''] as string[],
    brandVoice: '',
    marketLocation: '',
    contentGoals: '',
    scraperSourceUrls: [''] as string[],
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim() && !formData.url.trim()) {
      toast.error('Please provide at least a business name or website URL.');
      return;
    }
    setStep('creating');

    try {
      await webAppApi.create({
        ...formData,
        keyFeatures: formData.keyFeatures.filter(f => f.trim() !== ''),
        brandVoice: formData.brandVoice.trim() || undefined,
        marketLocation: formData.marketLocation.trim() || undefined,
        contentGoals: formData.contentGoals.trim() || undefined,
        scraperSourceUrls: formData.scraperSourceUrls.filter(u => u.trim() !== '').length > 0
          ? formData.scraperSourceUrls.filter(u => u.trim() !== '')
          : undefined,
        isActive: true,
      });

      // Show scraping state while backend auto-scrapes in background
      setStep('scraping');
      await new Promise(r => setTimeout(r, 1800)); // brief visual pause

      setStep('done');
      await new Promise(r => setTimeout(r, 900));

      toast.success('Business added! AI is scanning your website for content insights.');
      navigate('/dashboard/webapps');
    } catch (error) {
      setStep('idle');
      toast.error('Failed to add web app');
    }
  };

  const addFeature = () => setFormData({ ...formData, keyFeatures: [...formData.keyFeatures, ''] });
  const removeFeature = (index: number) =>
    setFormData({ ...formData, keyFeatures: formData.keyFeatures.filter((_, i) => i !== index) });
  const updateFeature = (index: number, value: string) => {
    const next = [...formData.keyFeatures];
    next[index] = value;
    setFormData({ ...formData, keyFeatures: next });
  };

  const addScraperUrl = () => setFormData({ ...formData, scraperSourceUrls: [...formData.scraperSourceUrls, ''] });
  const removeScraperUrl = (index: number) =>
    setFormData({ ...formData, scraperSourceUrls: formData.scraperSourceUrls.filter((_, i) => i !== index) });
  const updateScraperUrl = (index: number, value: string) => {
    const next = [...formData.scraperSourceUrls];
    next[index] = value;
    setFormData({ ...formData, scraperSourceUrls: next });
  };

  const isSubmitting = step !== 'idle';

  return (
    <div className="max-w-2xl mx-auto">
      <Button variant="ghost" className="mb-4" onClick={() => navigate('/dashboard/webapps')}>
        <ArrowLeft className="w-4 h-4 mr-2" />
        Back to Businesses
      </Button>

      {/* Step progress overlay */}
      {isSubmitting && (
        <motion.div
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-4"
        >
          <Card className={`border-2 ${step === 'done' ? 'border-green-400 bg-green-50' : 'border-violet-400 bg-violet-50'}`}>
            <CardContent className="p-4 flex items-center gap-3">
              {step === 'creating' && <Loader2 className="w-5 h-5 text-violet-600 animate-spin" />}
              {step === 'scraping' && <Globe className="w-5 h-5 text-violet-600 animate-pulse" />}
              {step === 'done' && <CheckCircle2 className="w-5 h-5 text-green-600" />}
              <div>
                <p className="font-medium text-sm">
                  {step === 'creating' && 'Creating your business…'}
                  {step === 'scraping' && 'AI is scanning your website for content insights…'}
                  {step === 'done' && 'Done! Redirecting…'}
                </p>
                {step === 'scraping' && (
                  <p className="text-xs text-gray-500 mt-0.5">
                    Extracting headings, descriptions, and social links to fuel AI content generation
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-violet-600" />
            Add New Business
          </CardTitle>
          <p className="text-sm text-gray-500">
            The AI will instantly scan your website and start generating platform-optimised content.
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <motion.div custom={0} variants={fadeUp} initial="hidden" animate="show" className="space-y-2">
              <Label htmlFor="name">Business Name</Label>
              <Input
                id="name"
                placeholder="e.g., TaskFlow Pro"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                disabled={isSubmitting}
              />
            </motion.div>

            <motion.div custom={1} variants={fadeUp} initial="hidden" animate="show" className="space-y-2">
              <Label htmlFor="url">Website URL</Label>
              <Input
                id="url"
                type="url"
                placeholder="https://yourapp.com"
                value={formData.url}
                onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                disabled={isSubmitting}
              />
              <p className="text-xs text-gray-500 flex items-center gap-1">
                <Globe className="w-3 h-3" />
                AI will auto-scrape this URL for brand copy, headings and social links
              </p>
            </motion.div>

            <motion.div custom={2} variants={fadeUp} initial="hidden" animate="show" className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="What does your business do? What problem does it solve?"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={3}
                disabled={isSubmitting}
              />
            </motion.div>

            <motion.div custom={3} variants={fadeUp} initial="hidden" animate="show" className="space-y-2">
              <Label>Category *</Label>
              <div className="flex flex-wrap gap-2">
                {categories.map((cat) => (
                  <Badge
                    key={cat}
                    variant={formData.category === cat ? 'default' : 'outline'}
                    className={`cursor-pointer ${
                      formData.category === cat
                        ? 'bg-violet-600 hover:bg-violet-700'
                        : 'hover:bg-gray-100'
                    }`}
                    onClick={() => !isSubmitting && setFormData({ ...formData, category: cat })}
                  >
                    {cat}
                  </Badge>
                ))}
              </div>
            </motion.div>

            <motion.div custom={4} variants={fadeUp} initial="hidden" animate="show" className="space-y-2">
              <Label htmlFor="targetAudience">Target Audience</Label>
              <Input
                id="targetAudience"
                placeholder="e.g., Remote teams, project managers, startups"
                value={formData.targetAudience}
                onChange={(e) => setFormData({ ...formData, targetAudience: e.target.value })}
                disabled={isSubmitting}
              />
            </motion.div>

            <motion.div custom={5} variants={fadeUp} initial="hidden" animate="show" className="space-y-2">
              <Label>Key Features</Label>
              <p className="text-sm text-gray-500 mb-2">
                Add features that make your business stand out — helps AI create better content.
              </p>
              <div className="space-y-2">
                {formData.keyFeatures.map((feature, index) => (
                  <div key={index} className="flex items-center space-x-2">
                    <Input
                      placeholder={`Feature ${index + 1}`}
                      value={feature}
                      onChange={(e) => updateFeature(index, e.target.value)}
                      disabled={isSubmitting}
                    />
                    {formData.keyFeatures.length > 1 && (
                      <Button type="button" variant="ghost" size="icon" onClick={() => removeFeature(index)}>
                        <X className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                ))}
              </div>
              <Button type="button" variant="outline" size="sm" onClick={addFeature} disabled={isSubmitting}>
                <Plus className="w-4 h-4 mr-2" />
                Add Feature
              </Button>
            </motion.div>

            <motion.div custom={6} variants={fadeUp} initial="hidden" animate="show" className="space-y-2">
              <Label htmlFor="brandVoice">Brand Voice &amp; Tone</Label>
              <Textarea
                id="brandVoice"
                placeholder="Describe your brand's voice and tone. e.g. 'Professional yet approachable, uses plain language, avoids jargon, energetic and motivating.'"
                value={formData.brandVoice}
                onChange={(e) => setFormData({ ...formData, brandVoice: e.target.value })}
                rows={3}
                disabled={isSubmitting}
              />
              <p className="text-xs text-gray-500">
                This guides AI content generation to match your brand personality.
              </p>
            </motion.div>

            <motion.div custom={7} variants={fadeUp} initial="hidden" animate="show" className="space-y-2">
              <Label htmlFor="marketLocation">Market / Location</Label>
              <Input
                id="marketLocation"
                placeholder="e.g., United Kingdom, Global, US - New York"
                value={formData.marketLocation}
                onChange={(e) => setFormData({ ...formData, marketLocation: e.target.value })}
                disabled={isSubmitting}
              />
              <p className="text-xs text-gray-500">
                The geographic market or region you are targeting.
              </p>
            </motion.div>

            <motion.div custom={8} variants={fadeUp} initial="hidden" animate="show" className="space-y-2">
              <Label htmlFor="contentGoals">Content Goals</Label>
              <Textarea
                id="contentGoals"
                placeholder="e.g., Drive app signups, build brand awareness, grow newsletter subscribers"
                value={formData.contentGoals}
                onChange={(e) => setFormData({ ...formData, contentGoals: e.target.value })}
                rows={3}
                disabled={isSubmitting}
              />
              <p className="text-xs text-gray-500">
                What do you want your content to achieve? This shapes AI generation priorities.
              </p>
            </motion.div>

            <motion.div custom={9} variants={fadeUp} initial="hidden" animate="show" className="space-y-2">
              <Label>Additional Scraper Source URLs</Label>
              <p className="text-sm text-gray-500 mb-2">
                Add extra pages to scrape (e.g. product pages, pricing, about). The main URL above is always scraped automatically.
              </p>
              <div className="space-y-2">
                {formData.scraperSourceUrls.map((url, index) => (
                  <div key={index} className="flex items-center space-x-2">
                    <Input
                      type="url"
                      placeholder={`https://yourapp.com/page-${index + 1}`}
                      value={url}
                      onChange={(e) => updateScraperUrl(index, e.target.value)}
                      disabled={isSubmitting}
                    />
                    {formData.scraperSourceUrls.length > 1 && (
                      <Button type="button" variant="ghost" size="icon" onClick={() => removeScraperUrl(index)} disabled={isSubmitting}>
                        <X className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                ))}
              </div>
              <Button type="button" variant="outline" size="sm" onClick={addScraperUrl} disabled={isSubmitting}>
                <Plus className="w-4 h-4 mr-2" />
                Add URL
              </Button>
            </motion.div>

            <motion.div custom={10} variants={fadeUp} initial="hidden" animate="show" className="flex items-center justify-end space-x-4 pt-4">
              <Button type="button" variant="outline" onClick={() => navigate('/dashboard/webapps')} disabled={isSubmitting}>
                Cancel
              </Button>
              <Button
                type="submit"
                className="bg-gradient-to-r from-violet-600 to-indigo-600"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    {step === 'creating' ? 'Creating…' : step === 'scraping' ? 'AI Scanning…' : 'Done!'}
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 mr-2" />
                    Add Business & Start AI
                  </>
                )}
              </Button>
            </motion.div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
