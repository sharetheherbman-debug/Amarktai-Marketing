import { useEffect, useState } from 'react';
import { TrendingUp, Eye, Heart, MousePointer, Download, Upload, Brain } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { AnalyticsSummary } from '@/types';
import { analyticsApi } from '@/lib/api';
import { toast } from 'sonner';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';

const platformColors: Record<string, string> = {
  youtube: '#FF0000',
  tiktok: '#000000',
  instagram: '#E4405F',
  facebook: '#1877F2',
  twitter: '#000000',
  linkedin: '#0A66C2',
};

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('7d');
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    try {
      const data = await analyticsApi.getSummary();
      setAnalytics(data);
    } catch {
      console.error('Failed to load analytics');
    } finally {
      setLoading(false);
    }
  };

  const handleUploadCsv = async () => {
    if (!csvFile) {
      toast.error('Select a CSV file first.');
      return;
    }
    setUploading(true);
    try {
      const result = await analyticsApi.importMetricsCsv(csvFile);
      toast.success(`Imported ${result.imported} metric rows.`);
      setCsvFile(null);
      await fetchAnalytics();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'CSV import failed');
    } finally {
      setUploading(false);
    }
  };

  const statsCards = [
    {
      title: 'Total Posts',
      value: analytics?.totalPosts || 0,
      icon: TrendingUp,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      title: 'Total Views',
      value: (analytics?.totalViews ?? 0).toLocaleString(),
      icon: Eye,
      color: 'text-violet-600',
      bgColor: 'bg-violet-50',
    },
    {
      title: 'Total Engagement',
      value: (analytics?.totalEngagement ?? 0).toLocaleString(),
      icon: Heart,
      color: 'text-pink-600',
      bgColor: 'bg-pink-50',
    },
    {
      title: 'Average CTR',
      value: `${analytics?.avgCtr || 0}%`,
      icon: MousePointer,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
  ];

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6">
                <div className="h-4 bg-gray-200 rounded w-24 mb-4" />
                <div className="h-8 bg-gray-200 rounded w-16" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Analytics</h2>
          <p className="text-gray-500">Track your social media performance</p>
        </div>
        <div className="flex items-center space-x-3">
          <Badge variant={analytics?.learningActive ? 'default' : 'outline'}>
            <Brain className="w-3 h-3 mr-1" />
            {analytics?.learningActive ? 'Learning active' : 'Learning inactive'}
          </Badge>
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="border rounded-lg px-3 py-2 text-sm"
          >
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
          </select>
          <Button variant="outline">
            <Download className="w-4 h-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Learning Inputs</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-gray-500">
            Import platform metrics by CSV when direct social APIs are not connected.
            Fields: platform, impressions, reach, clicks, likes, comments, shares, saves, conversions.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 sm:items-center">
            <input
              type="file"
              accept=".csv"
              onChange={(e) => setCsvFile(e.target.files?.[0] || null)}
              className="text-sm"
            />
            <Button onClick={handleUploadCsv} disabled={uploading || !csvFile}>
              <Upload className="w-4 h-4 mr-2" />
              {uploading ? 'Importing…' : 'Import CSV'}
            </Button>
            <Badge variant="outline">Records: {analytics?.metricsRecords ?? 0}</Badge>
          </div>
        </CardContent>
      </Card>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statsCards.map((stat) => (
          <Card key={stat.title}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">{stat.title}</p>
                  <p className="text-2xl font-bold mt-1">{stat.value}</p>
                </div>
                <div className={`w-12 h-12 ${stat.bgColor} rounded-lg flex items-center justify-center`}>
                  <stat.icon className={`w-6 h-6 ${stat.color}`} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="platforms">Platforms</TabsTrigger>
          <TabsTrigger value="engagement">Engagement</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Views Over Time</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={analytics?.dailyStats || []}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip formatter={(value: number) => value.toLocaleString()} />
                    <Line type="monotone" dataKey="views" stroke="#7c3aed" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Engagement Over Time</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={analytics?.dailyStats || []}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip formatter={(value: number) => value.toLocaleString()} />
                    <Line type="monotone" dataKey="engagement" stroke="#ec4899" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="platforms">
          <Card>
            <CardHeader>
              <CardTitle>Platform Performance</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={analytics ? Object.entries(analytics.platformBreakdown).map(([platform, stats]) => ({
                      platform,
                      views: stats.views,
                      engagement: stats.engagement,
                    })) : []}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="platform" tickFormatter={(p) => p.charAt(0).toUpperCase() + p.slice(1)} />
                    <YAxis />
                    <Tooltip formatter={(value: number) => value.toLocaleString()} />
                    <Bar dataKey="views" fill="#7c3aed" name="Views" />
                    <Bar dataKey="engagement" fill="#ec4899" name="Engagement" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Platform Breakdown</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-3 px-4">Platform</th>
                      <th className="text-right py-3 px-4">Posts</th>
                      <th className="text-right py-3 px-4">Views</th>
                      <th className="text-right py-3 px-4">Engagement</th>
                      <th className="text-right py-3 px-4">CTR</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analytics && Object.entries(analytics.platformBreakdown).map(([platform, stats]) => (
                      <tr key={platform} className="border-b last:border-0">
                        <td className="py-3 px-4">
                          <div className="flex items-center">
                            <div className="w-3 h-3 rounded-full mr-2" style={{ backgroundColor: platformColors[platform] }} />
                            <span className="capitalize font-medium">{platform}</span>
                          </div>
                        </td>
                        <td className="text-right py-3 px-4">{stats.posts}</td>
                        <td className="text-right py-3 px-4">{stats.views.toLocaleString()}</td>
                        <td className="text-right py-3 px-4">{stats.engagement.toLocaleString()}</td>
                        <td className="text-right py-3 px-4"><Badge variant="outline">{stats.ctr}%</Badge></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="engagement">
          <Card>
            <CardHeader>
              <CardTitle>Engagement Metrics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-3 gap-6">
                <div className="text-center p-6 bg-violet-50 rounded-lg">
                  <p className="text-3xl font-bold text-violet-600">
                    {((analytics?.totalEngagement || 0) / (analytics?.totalViews || 1) * 100).toFixed(1)}%
                  </p>
                  <p className="text-gray-600 mt-1">Engagement Rate</p>
                </div>
                <div className="text-center p-6 bg-pink-50 rounded-lg">
                  <p className="text-3xl font-bold text-pink-600">{analytics?.avgCtr || 0}%</p>
                  <p className="text-gray-600 mt-1">Average CTR</p>
                </div>
                <div className="text-center p-6 bg-green-50 rounded-lg">
                  <p className="text-3xl font-bold text-green-600">
                    {Math.round((analytics?.totalViews || 0) / (analytics?.totalPosts || 1)).toLocaleString()}
                  </p>
                  <p className="text-gray-600 mt-1">Avg Views per Post</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
