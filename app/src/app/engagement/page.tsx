import { useEffect, useState } from 'react';
import { 
  MessageSquare, 
  Check, 
  X, 
  RefreshCw, 
  AlertTriangle,
  Send,
  Sparkles,
  Clock,
  TrendingUp
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { toast } from 'sonner';
import { motion, AnimatePresence } from 'framer-motion';

interface Engagement {
  id: string;
  platform: string;
  engagement_type: string;
  author_name: string;
  original_text: string;
  ai_reply_text: string | null;
  ai_reply_confidence: number | null;
  status: 'pending' | 'generating' | 'ready' | 'approved' | 'sent' | 'rejected';
  priority: 'high' | 'medium' | 'low';
  auto_reply_safe: boolean;
  risk_factors: string[];
  sentiment: string;
  created_at: string;
}

interface EngagementStats {
  by_status: Record<string, number>;
  by_platform: Record<string, number>;
  pending_count: number;
  total_engagements: number;
}

const PLATFORM_ICONS: Record<string, string> = {
  youtube: '🔴',
  tiktok: '🎵',
  instagram: '📷',
  facebook: '👥',
  twitter: '🐦',
  linkedin: '💼',
};

const SENTIMENT_COLORS: Record<string, string> = {
  positive: 'bg-green-100 text-green-700',
  negative: 'bg-red-100 text-red-700',
  neutral: 'bg-gray-100 text-gray-700',
};

const PRIORITY_COLORS: Record<string, string> = {
  high: 'bg-red-100 text-red-700 border-red-200',
  medium: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  low: 'bg-blue-100 text-blue-700 border-blue-200',
};

export default function EngagementPage() {
  const [engagements, setEngagements] = useState<Engagement[]>([]);
  const [stats, setStats] = useState<EngagementStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedEngagement, setSelectedEngagement] = useState<Engagement | null>(null);
  const [editedReply, setEditedReply] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState('pending');

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [activeTab]);

  const fetchData = async () => {
    try {
      setIsLoading(true);
      
      // Fetch engagements
      const status = activeTab === 'all' ? '' : activeTab;
      const res = await fetch(`/api/v1/engagement/queue?status=${status}&limit=50`);
      if (res.ok) {
        setEngagements(await res.json());
      }
      
      // Fetch stats
      const statsRes = await fetch('/api/v1/engagement/stats');
      if (statsRes.ok) {
        setStats(await statsRes.json());
      }
    } catch (error) {
      toast.error('Failed to load engagements');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAction = async (engagementId: string, action: string, editedText?: string) => {
    setIsSubmitting(true);
    try {
      const res = await fetch(`/api/v1/engagement/${engagementId}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, edited_text: editedText }),
      });

      if (res.ok) {
        toast.success(action === 'approve' ? 'Reply sent!' : action === 'reject' ? 'Engagement rejected' : 'Reply updated');
        setSelectedEngagement(null);
        fetchData();
      } else {
        toast.error('Action failed');
      }
    } catch (error) {
      toast.error('Error processing action');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRegenerate = async (engagementId: string) => {
    try {
      const res = await fetch(`/api/v1/engagement/${engagementId}/regenerate`, {
        method: 'POST',
      });

      if (res.ok) {
        toast.success('Regenerating reply...');
        fetchData();
      } else {
        toast.error('Failed to regenerate');
      }
    } catch (error) {
      toast.error('Error regenerating reply');
    }
  };

  const openEngagement = (engagement: Engagement) => {
    setSelectedEngagement(engagement);
    setEditedReply(engagement.ai_reply_text || '');
  };

  const pendingEngagements = engagements.filter(e => ['pending', 'generating', 'ready'].includes(e.status));
    return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Engagement Approval Queue</h2>
          <p className="text-gray-500">Review and approve AI-generated replies to comments and DMs</p>
        </div>
        <Button variant="outline" onClick={fetchData}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Pending Review</p>
                  <p className="text-2xl font-bold text-amber-600">{stats.pending_count}</p>
                </div>
                <div className="p-3 bg-amber-100 rounded-lg">
                  <Clock className="w-5 h-5 text-amber-600" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Total Engagements</p>
                  <p className="text-2xl font-bold">{stats.total_engagements}</p>
                </div>
                <div className="p-3 bg-blue-100 rounded-lg">
                  <MessageSquare className="w-5 h-5 text-blue-600" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Sent Replies</p>
                  <p className="text-2xl font-bold text-green-600">{stats.by_status?.sent || 0}</p>
                </div>
                <div className="p-3 bg-green-100 rounded-lg">
                  <Send className="w-5 h-5 text-green-600" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Response Rate</p>
                  <p className="text-2xl font-bold text-purple-600">
                    {stats.total_engagements > 0 
                      ? Math.round(((stats.by_status?.sent || 0) / stats.total_engagements) * 100) 
                      : 0}%
                  </p>
                </div>
                <div className="p-3 bg-purple-100 rounded-lg">
                  <TrendingUp className="w-5 h-5 text-purple-600" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Engagements List */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="pending">
            Pending ({pendingEngagements.length})
          </TabsTrigger>
          <TabsTrigger value="sent">Sent</TabsTrigger>
          <TabsTrigger value="all">All</TabsTrigger>
        </TabsList>

        <TabsContent value={activeTab} className="space-y-4">
          {isLoading ? (
            <div className="text-center py-12">
              <RefreshCw className="w-8 h-8 animate-spin mx-auto text-gray-400" />
              <p className="text-gray-500 mt-4">Loading engagements...</p>
            </div>
          ) : engagements.length === 0 ? (
            <div className="text-center py-12">
              <MessageSquare className="w-12 h-12 mx-auto text-gray-300 mb-4" />
              <p className="text-gray-500">No engagements to review</p>
              <p className="text-sm text-gray-400">New comments and DMs will appear here</p>
            </div>
          ) : (
            <div className="space-y-3">
              <AnimatePresence>
                {engagements.map((engagement) => (
                  <motion.div
                    key={engagement.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    onClick={() => openEngagement(engagement)}
                    className="p-4 bg-white border rounded-lg cursor-pointer hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-3">
                        <div className="text-2xl">{PLATFORM_ICONS[engagement.platform] || '💬'}</div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium">{engagement.author_name}</span>
                            <Badge variant="outline" className={SENTIMENT_COLORS[engagement.sentiment] || ''}>
                              {engagement.sentiment}
                            </Badge>
                            <Badge variant="outline" className={PRIORITY_COLORS[engagement.priority]}>
                              {engagement.priority} priority
                            </Badge>
                            {engagement.auto_reply_safe && (
                              <Badge className="bg-green-100 text-green-700">Auto-safe</Badge>
                            )}
                          </div>
                          <p className="text-gray-700 line-clamp-2">{engagement.original_text}</p>
                          
                          {engagement.ai_reply_text && (
                            <div className="mt-3 p-3 bg-blue-50 rounded-lg">
                              <div className="flex items-center gap-2 mb-1">
                                <Sparkles className="w-4 h-4 text-blue-500" />
                                <span className="text-sm text-blue-600 font-medium">AI Reply</span>
                                {engagement.ai_reply_confidence && (
                                  <span className="text-xs text-blue-400">
                                    {Math.round(engagement.ai_reply_confidence * 100)}% confidence
                                  </span>
                                )}
                              </div>
                              <p className="text-gray-700 text-sm">{engagement.ai_reply_text}</p>
                            </div>
                          )}

                          {engagement.risk_factors.length > 0 && (
                            <div className="mt-2 flex items-center gap-1 text-amber-600 text-sm">
                              <AlertTriangle className="w-4 h-4" />
                              <span>{engagement.risk_factors[0]}</span>
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {engagement.status === 'generating' && (
                          <Badge variant="outline">
                            <RefreshCw className="w-3 h-3 animate-spin mr-1" />
                            Generating...
                          </Badge>
                        )}
                        {engagement.status === 'ready' && (
                          <Badge className="bg-blue-100 text-blue-700">Ready</Badge>
                        )}
                        {engagement.status === 'sent' && (
                          <Badge className="bg-green-100 text-green-700">
                            <Check className="w-3 h-3 mr-1" />
                            Sent
                          </Badge>
                        )}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Engagement Detail Dialog */}
      <Dialog open={!!selectedEngagement} onOpenChange={() => setSelectedEngagement(null)}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          {selectedEngagement && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <span className="text-2xl">{PLATFORM_ICONS[selectedEngagement.platform]}</span>
                  Review Engagement
                </DialogTitle>
                <DialogDescription className="sr-only">
                  Review and edit the suggested engagement reply before approving or sending.
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-6">
                {/* Original Message */}
                <div>
                  <p className="text-sm text-gray-500 mb-2">Original Message from {selectedEngagement.author_name}</p>
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <p className="text-gray-800">{selectedEngagement.original_text}</p>
                  </div>
                  <div className="flex gap-2 mt-2">
                    <Badge variant="outline" className={SENTIMENT_COLORS[selectedEngagement.sentiment]}>
                      {selectedEngagement.sentiment} sentiment
                    </Badge>
                    <Badge variant="outline" className={PRIORITY_COLORS[selectedEngagement.priority]}>
                      {selectedEngagement.priority} priority
                    </Badge>
                  </div>
                </div>

                {/* AI Reply */}
                {selectedEngagement.ai_reply_text && (
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Sparkles className="w-4 h-4 text-blue-500" />
                      <p className="text-sm font-medium">AI-Generated Reply</p>
                      {selectedEngagement.ai_reply_confidence && (
                        <span className="text-xs text-gray-500">
                          {Math.round(selectedEngagement.ai_reply_confidence * 100)}% confidence
                        </span>
                      )}
                    </div>
                    <Textarea
                      value={editedReply}
                      onChange={(e) => setEditedReply(e.target.value)}
                      rows={4}
                      className="resize-none"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      You can edit the reply before sending
                    </p>
                  </div>
                )}

                {/* Risk Factors */}
                {selectedEngagement.risk_factors.length > 0 && (
                  <div className="p-4 bg-amber-50 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <AlertTriangle className="w-4 h-4 text-amber-600" />
                      <p className="text-sm font-medium text-amber-800">Risk Factors</p>
                    </div>
                    <ul className="text-sm text-amber-700 space-y-1">
                      {selectedEngagement.risk_factors.map((factor, i) => (
                        <li key={i}>• {factor}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Actions */}
                <div className="flex justify-end gap-3">
                  <Button
                    variant="outline"
                    onClick={() => handleRegenerate(selectedEngagement.id)}
                    disabled={isSubmitting}
                  >
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Regenerate
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => handleAction(selectedEngagement.id, 'reject')}
                    disabled={isSubmitting}
                  >
                    <X className="w-4 h-4 mr-2" />
                    Skip
                  </Button>
                  <Button
                    onClick={() => handleAction(selectedEngagement.id, 'edit', editedReply)}
                    disabled={isSubmitting}
                    className="bg-gradient-to-r from-violet-600 to-indigo-600"
                  >
                    <Send className="w-4 h-4 mr-2" />
                    Send Reply
                  </Button>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
