import { useEffect, useState } from 'react';
import { Check, X, Edit2, RefreshCw, Calendar, Clock, CheckCircle, Sparkles, BarChart3 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { Content } from '@/types';
import { contentApi } from '@/lib/api';
import { toast } from 'sonner';
import { format } from 'date-fns';
import PerformancePredictor from '@/components/dashboard/PerformancePredictor';
import { ABTestingPanel } from '@/components/dashboard/ABTestingPanel';

const platformIcons: Record<string, string> = {
  youtube: '▶️',
  tiktok: '🎵',
  instagram: '📷',
  facebook: '👥',
  twitter: '🐦',
  linkedin: '💼',
};

export default function ApprovalPage() {
  const [pendingContent, setPendingContent] = useState<Content[]>([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState<string[]>([]);
  const [editingContent, setEditingContent] = useState<Content | null>(null);
  const [editCaption, setEditCaption] = useState('');

  useEffect(() => {
    fetchPendingContent();
  }, []);

  const fetchPendingContent = async () => {
    try {
      const data = await contentApi.getPending();
      setPendingContent(data);
    } catch (error) {
      toast.error('Failed to load pending content');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (id: string) => {
    setProcessing([...processing, id]);
    try {
      await contentApi.approve(id);
      setPendingContent(pendingContent.filter(c => c.id !== id));
      toast.success('Content approved and scheduled');
    } catch (error) {
      toast.error('Failed to approve content');
    } finally {
      setProcessing(processing.filter(pid => pid !== id));
    }
  };

  const handleReject = async (id: string) => {
    setProcessing([...processing, id]);
    try {
      await contentApi.reject(id);
      setPendingContent(pendingContent.filter(c => c.id !== id));
      toast.success('Content rejected');
    } catch (error) {
      toast.error('Failed to reject content');
    } finally {
      setProcessing(processing.filter(pid => pid !== id));
    }
  };

  const handleApproveAll = async () => {
    if (pendingContent.length === 0) return;
    
    const ids = pendingContent.map(c => c.id);
    setProcessing([...processing, ...ids]);
    
    try {
      await contentApi.approveAll(ids);
      setPendingContent([]);
      toast.success(`Approved ${ids.length} items`);
    } catch (error) {
      toast.error('Failed to approve all content');
    } finally {
      setProcessing([]);
    }
  };

  const handleEdit = (content: Content) => {
    setEditingContent(content);
    setEditCaption(content.caption);
  };

  const handleSaveEdit = async () => {
    if (!editingContent) return;
    
    try {
      await contentApi.updateCaption(editingContent.id, editCaption);
      setPendingContent(pendingContent.map(c => 
        c.id === editingContent.id ? { ...c, caption: editCaption } : c
      ));
      toast.success('Caption updated');
      setEditingContent(null);
    } catch (error) {
      toast.error('Failed to update caption');
    }
  };

  const handleRegenerate = async (content: Content) => {
    setProcessing([...processing, content.id]);
    try {
      const newContent = await contentApi.generate(content.webappId, content.platform);
      setPendingContent(pendingContent.map(c => 
        c.id === content.id ? newContent : c
      ));
      toast.success('Content regenerated');
    } catch (error) {
      toast.error('Failed to regenerate content');
    } finally {
      setProcessing(processing.filter(pid => pid !== content.id));
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-8 bg-gray-200 rounded w-48" />
        <div className="grid gap-4">
          {[...Array(3)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6">
                <div className="h-4 bg-gray-200 rounded w-3/4" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Content Review</h2>
          <p className="text-gray-500">
            Review, predict performance, and optimize before publishing
          </p>
        </div>
        {pendingContent.length > 0 && (
          <div className="flex items-center space-x-3">
            <Button
              variant="outline"
              onClick={() => {
                if (confirm(`Reject all ${pendingContent.length} items?`)) {
                  Promise.all(pendingContent.map(c => handleReject(c.id)));
                }
              }}
            >
              <X className="w-4 h-4 mr-2" />
              Reject All
            </Button>
            <Button
              className="bg-gradient-to-r from-violet-600 to-indigo-600"
              onClick={handleApproveAll}
              disabled={processing.length > 0}
            >
              <Check className="w-4 h-4 mr-2" />
              Approve All ({pendingContent.length})
            </Button>
          </div>
        )}
      </div>

      {/* Main Tabs */}
      <Tabs defaultValue="queue" className="w-full">
        <TabsList className="grid grid-cols-3 w-full max-w-md">
          <TabsTrigger value="queue">
            <CheckCircle className="w-4 h-4 mr-2" />
            Queue ({pendingContent.length})
          </TabsTrigger>
          <TabsTrigger value="predictor">
            <Sparkles className="w-4 h-4 mr-2" />
            AI Predictor
          </TabsTrigger>
          <TabsTrigger value="abtest">
            <BarChart3 className="w-4 h-4 mr-2" />
            A/B Testing
          </TabsTrigger>
        </TabsList>

        <TabsContent value="queue" className="space-y-6">
          {/* Info Banner */}
          {pendingContent.length > 0 ? (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start">
              <Clock className="w-5 h-5 text-blue-600 mr-3 mt-0.5" />
              <div>
                <p className="text-blue-900 font-medium">
                  {pendingContent.length} items waiting for approval
                </p>
                <p className="text-blue-700 text-sm">
                  Approved content will be posted at the optimal time for each platform.
                  You can edit captions before approving.
                </p>
              </div>
            </div>
          ) : (
            <div className="bg-green-50 border border-green-200 rounded-lg p-8 text-center">
              <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-green-900 mb-2">All Caught Up!</h3>
              <p className="text-green-700 max-w-md mx-auto">
                No content waiting for approval. New content will be generated tonight at 2:00 AM.
              </p>
            </div>
          )}

          {/* Content Cards */}
      <div className="space-y-4">
        {pendingContent.map((content) => (
          <Card key={content.id} className="overflow-hidden">
            <CardContent className="p-0">
              <div className="flex flex-col lg:flex-row">
                {/* Media Preview */}
                <div className="w-full lg:w-64 h-48 lg:h-auto bg-gray-100 flex-shrink-0">
                  {content.mediaUrls[0] ? (
                    <img 
                      src={content.mediaUrls[0]} 
                      alt={content.title}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-400">
                      <span className="text-6xl">{platformIcons[content.platform]}</span>
                    </div>
                  )}
                </div>

                {/* Content Details */}
                <div className="flex-1 p-6">
                  <div className="flex items-center space-x-2 mb-3">
                    <span className="text-2xl">{platformIcons[content.platform]}</span>
                    <Badge variant="outline" className="capitalize">
                      {content.platform}
                    </Badge>
                    <Badge variant="outline" className="capitalize">
                      {content.type}
                    </Badge>
                    <span className="text-sm text-gray-500 flex items-center">
                      <Calendar className="w-4 h-4 mr-1" />
                      Generated {format(new Date(content.createdAt), 'MMM d, h:mm a')}
                    </span>
                  </div>

                  <h3 className="font-semibold text-xl mb-2">{content.title}</h3>
                  <p className="text-gray-600 mb-4 whitespace-pre-line">
                    {content.caption}
                  </p>

                  <div className="flex flex-wrap gap-2 mb-4">
                    {content.hashtags.map((tag, i) => (
                      <span key={i} className="text-sm text-violet-600 bg-violet-50 px-2 py-1 rounded">
                        #{tag}
                      </span>
                    ))}
                  </div>

                  {/* Action Buttons */}
                  <div className="flex flex-wrap items-center gap-3 pt-4 border-t">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleEdit(content)}
                    >
                      <Edit2 className="w-4 h-4 mr-2" />
                      Edit Caption
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleRegenerate(content)}
                      disabled={processing.includes(content.id)}
                    >
                      <RefreshCw className="w-4 h-4 mr-2" />
                      Regenerate
                    </Button>
                    <div className="flex-1" />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleReject(content.id)}
                      disabled={processing.includes(content.id)}
                      className="text-red-600 hover:text-red-700 hover:bg-red-50"
                    >
                      <X className="w-4 h-4 mr-2" />
                      Reject
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => handleApprove(content.id)}
                      disabled={processing.includes(content.id)}
                      className="bg-gradient-to-r from-violet-600 to-indigo-600"
                    >
                      <Check className="w-4 h-4 mr-2" />
                      {processing.includes(content.id) ? 'Processing...' : 'Approve'}
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Edit Dialog */}
      <Dialog open={!!editingContent} onOpenChange={() => setEditingContent(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit Caption</DialogTitle>
            <DialogDescription className="sr-only">
              Edit generated caption text before approving and scheduling the content.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Textarea
              value={editCaption}
              onChange={(e) => setEditCaption(e.target.value)}
              rows={8}
              className="resize-none"
            />
            <div className="flex justify-end space-x-3">
              <Button variant="outline" onClick={() => setEditingContent(null)}>
                Cancel
              </Button>
              <Button 
                className="bg-gradient-to-r from-violet-600 to-indigo-600"
                onClick={handleSaveEdit}
              >
                Save Changes
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
        </TabsContent>

        <TabsContent value="predictor">
          <PerformancePredictor />
        </TabsContent>

        <TabsContent value="abtest">
          <ABTestingPanel />
        </TabsContent>
      </Tabs>
    </div>
  );
}
