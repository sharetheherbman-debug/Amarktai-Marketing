import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Key, Check, X, ExternalLink, RefreshCw, AlertCircle,
  Youtube, Instagram, Facebook, Twitter, Linkedin, Music, Settings, Plus,
  Trash2, Eye, EyeOff, MessageSquare, Cloud, AtSign, Send, Camera, Pin,
  Sparkles, Globe, ChevronRight, CheckCircle2, Loader2,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import { PLATFORM_COUNT } from '@/lib/platformConstants';
import { getStoredToken } from '@/lib/auth';

interface APIKey {
  id: string;
  key_name: string;
  is_active: boolean;
  created_at: string;
}

interface PlatformIntegration {
  platform: string;
  is_connected: boolean;
  connected_at: string | null;
  platform_username: string | null;
  auto_post_enabled: boolean;
  auto_reply_enabled: boolean;
  low_risk_auto_reply: boolean;
}

const AVAILABLE_API_KEYS = [
  { key: 'GENX_API_KEY', name: 'GenX API Key', description: 'Primary unified AI provider for all AI features (REQUIRED)', provider: 'GenX', required: true },
  { key: 'FIRECRAWL_API_KEY', name: 'Firecrawl API Key', description: 'Web scraping & competitive research (REQUIRED)', provider: 'Firecrawl', required: true },
  { key: 'QWEN_API_KEY', name: 'Qwen / DashScope API Key', description: 'Legacy fallback provider', provider: 'Qwen (DashScope)', required: false },
  { key: 'HUGGINGFACE_TOKEN', name: 'HuggingFace Token', description: 'Legacy fallback provider', provider: 'HuggingFace', required: false },
  { key: 'OPENAI_API_KEY', name: 'OpenAI API Key', description: 'Optional compatibility fallback', provider: 'OpenAI', required: false },
  { key: 'GEMINI_API_KEY', name: 'Google Gemini API Key', description: 'Optional compatibility fallback', provider: 'Google Gemini', required: false },
];

const PLATFORMS = [
  { id: 'youtube', name: 'YouTube', icon: Youtube, color: 'text-red-500', bgColor: 'bg-red-500/10', description: 'Upload Shorts & long-form videos' },
  { id: 'tiktok', name: 'TikTok', icon: Music, color: 'text-pink-500', bgColor: 'bg-pink-500/10', description: 'Post short-form viral videos' },
  { id: 'instagram', name: 'Instagram', icon: Instagram, color: 'text-purple-500', bgColor: 'bg-purple-500/10', description: 'Posts, Stories, Reels' },
  { id: 'facebook', name: 'Facebook', icon: Facebook, color: 'text-blue-500', bgColor: 'bg-blue-500/10', description: 'Page posts and Reels' },
  { id: 'twitter', name: 'Twitter / X', icon: Twitter, color: 'text-sky-500', bgColor: 'bg-sky-500/10', description: 'Tweets and threads' },
  { id: 'linkedin', name: 'LinkedIn', icon: Linkedin, color: 'text-blue-600', bgColor: 'bg-blue-600/10', description: 'Professional posts and articles' },
  { id: 'pinterest', name: 'Pinterest', icon: Pin, color: 'text-red-600', bgColor: 'bg-red-600/10', description: 'Pins and idea boards' },
  { id: 'reddit', name: 'Reddit', icon: MessageSquare, color: 'text-orange-500', bgColor: 'bg-orange-500/10', description: 'Posts and community threads' },
  { id: 'bluesky', name: 'Bluesky', icon: Cloud, color: 'text-sky-400', bgColor: 'bg-sky-400/10', description: 'Short posts on AT Protocol' },
  { id: 'threads', name: 'Threads', icon: AtSign, color: 'text-gray-800', bgColor: 'bg-gray-800/10', description: 'Text threads by Meta' },
  { id: 'telegram', name: 'Telegram', icon: Send, color: 'text-blue-400', bgColor: 'bg-blue-400/10', description: 'Channel and group messages' },
  { id: 'snapchat', name: 'Snapchat', icon: Camera, color: 'text-yellow-500', bgColor: 'bg-yellow-500/10', description: 'Stories and Spotlight' },
];

export default function IntegrationsPage() {
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [integrations, setIntegrations] = useState<PlatformIntegration[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showAddKeyDialog, setShowAddKeyDialog] = useState(false);
  const [selectedKeyType, setSelectedKeyType] = useState('');
  const [keyValue, setKeyValue] = useState('');
  const [showKeyValue, setShowKeyValue] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setIsLoading(true);
      const token = getStoredToken();
      const authHeaders: Record<string, string> = {};
      if (token) authHeaders.Authorization = `Bearer ${token}`;
      
      // Fetch API keys
      const keysRes = await fetch('/api/v1/integrations/api-keys', { headers: authHeaders });
      if (keysRes.ok) {
        setApiKeys(await keysRes.json());
      }
      
      // Fetch integrations
      const integrationsRes = await fetch('/api/v1/integrations/platforms', { headers: authHeaders });
      if (integrationsRes.ok) {
        setIntegrations(await integrationsRes.json());
      }
    } catch (error) {
      toast.error('Failed to load integrations');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddKey = async () => {
    if (!selectedKeyType || !keyValue) {
      toast.error('Please select key type and enter value');
      return;
    }

    setIsSaving(true);
    try {
      const token = getStoredToken();
      const res = await fetch('/api/v1/integrations/api-keys', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ key_name: selectedKeyType, key_value: keyValue }),
      });

      if (res.ok) {
        toast.success('API key saved successfully');
        setShowAddKeyDialog(false);
        setKeyValue('');
        setSelectedKeyType('');
        fetchData();
      } else {
        toast.error('Failed to save API key');
      }
    } catch (error) {
      toast.error('Error saving API key');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteKey = async (keyId: string) => {
    try {
      const token = getStoredToken();
      const res = await fetch(`/api/v1/integrations/api-keys/${keyId}`, {
        method: 'DELETE',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });

      if (res.ok) {
        toast.success('API key removed');
        fetchData();
      } else {
        toast.error('Failed to remove API key');
      }
    } catch (error) {
      toast.error('Error removing API key');
    }
  };

  const handleConnectPlatform = async (platform: string) => {
    try {
      const token = getStoredToken();
      const res = await fetch(`/api/v1/integrations/platforms/${platform}/connect`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        const data = await res.json();
        // Open OAuth popup
        const width = 500;
        const height = 600;
        const left = window.screenX + (window.outerWidth - width) / 2;
        const top = window.screenY + (window.outerHeight - height) / 2;
        window.open(
          data.auth_url,
          'Connect Platform',
          `width=${width},height=${height},left=${left},top=${top}`
        );
      } else {
        toast.error('Failed to initiate connection');
      }
    } catch (error) {
      toast.error('Error connecting platform');
    }
  };

  const handleDisconnectPlatform = async (platform: string) => {
    try {
      const token = getStoredToken();
      const res = await fetch(`/api/v1/integrations/platforms/${platform}/disconnect`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });

      if (res.ok) {
        toast.success(`${platform} disconnected`);
        fetchData();
      } else {
        toast.error('Failed to disconnect');
      }
    } catch (error) {
      toast.error('Error disconnecting platform');
    }
  };

  const handleUpdateIntegration = async (platform: string, updates: Partial<PlatformIntegration>) => {
    try {
      const token = getStoredToken();
      const res = await fetch(`/api/v1/integrations/platforms/${platform}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(updates),
      });

      if (res.ok) {
        fetchData();
      }
    } catch (error) {
      toast.error('Failed to update settings');
    }
  };

  const activeKeysCount = apiKeys.filter(k => k.is_active).length;
  const connectedPlatformsCount = integrations.filter(i => i.is_connected).length;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="w-8 h-8 animate-spin text-violet-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">API Keys & Integrations</h2>
        <p className="text-gray-500">Connect your accounts and add API keys for enhanced AI generation</p>
      </div>

      {/* Setup Wizard — shown when no keys added yet */}
      {activeKeysCount === 0 && (
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
          <Card className="border-2 border-violet-200 bg-gradient-to-br from-violet-50 to-indigo-50">
            <CardContent className="p-6">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="w-5 h-5 text-violet-600" />
                <h3 className="font-semibold text-violet-900">Setup Guide — Get Started in 3 Steps</h3>
              </div>
              <div className="space-y-3">
                {[
                  {
                    step: '1',
                    icon: Key,
                    title: 'Add GenX API Key (Primary AI Provider)',
                    desc: 'Required for AI content generation. Add your GenX key to enable all AI features.',
                    link: '#',
                    done: apiKeys.some(k => k.key_name === 'GENX_API_KEY' && k.is_active),
                  },
                  {
                    step: '2',
                    icon: Globe,
                    title: 'Add Firecrawl API Key (Web Scraping)',
                    desc: 'Required for website scraping and competitive research. Get your key at firecrawl.dev.',
                    link: '#',
                    done: apiKeys.some(k => k.key_name === 'FIRECRAWL_API_KEY' && k.is_active),
                  },
                  {
                    step: '3',
                    icon: Settings,
                    title: 'Connect your social media accounts',
                    desc: `Go to the Platforms page to connect all ${PLATFORM_COUNT} social accounts via OAuth.`,
                    link: '/dashboard/platforms',
                    done: integrations.some(i => i.is_connected),
                  },
                ].map((item) => (
                  <div key={item.step} className="flex items-start gap-3">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5 ${item.done ? 'bg-green-500 text-white' : 'bg-violet-200 text-violet-700'}`}>
                      {item.done ? <CheckCircle2 className="w-4 h-4" /> : item.step}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className={`text-sm font-medium ${item.done ? 'line-through text-gray-400' : 'text-gray-800'}`}>
                          {item.title}
                        </p>
                        {item.done && <span className="text-xs text-green-600 font-medium">Done</span>}
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5">{item.desc}</p>
                    </div>
                    {!item.done && (
                      <a href={item.link} target={item.link.startsWith('http') ? '_blank' : undefined} rel="noreferrer">
                        <ChevronRight className="w-4 h-4 text-violet-500" />
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Active API Keys</p>
                <p className="text-2xl font-bold">{activeKeysCount}</p>
              </div>
              <div className="p-3 bg-blue-100 rounded-lg">
                <Key className="w-5 h-5 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Connected Platforms</p>
                <p className="text-2xl font-bold">{connectedPlatformsCount}/{PLATFORM_COUNT}</p>
              </div>
              <div className="p-3 bg-green-100 rounded-lg">
                <Check className="w-5 h-5 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Auto-Posting</p>
                <p className="text-2xl font-bold">
                  {integrations.filter(i => i.auto_post_enabled).length}
                </p>
              </div>
              <div className="p-3 bg-purple-100 rounded-lg">
                <Settings className="w-5 h-5 text-purple-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* API Keys Section */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Key className="w-5 h-5" />
              Your API Keys
            </CardTitle>
            <CardDescription>
              Configure your provider API keys. GenX and Firecrawl are required for full functionality.
            </CardDescription>
          </div>
          <Button onClick={() => setShowAddKeyDialog(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Add Key
          </Button>
        </CardHeader>
        <CardContent>
          {apiKeys.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Key className="w-12 h-12 mx-auto mb-4 text-gray-300" />
              <p>No API keys added yet</p>
              <p className="text-sm">Add GenX and Firecrawl keys to get started</p>
            </div>
          ) : (
            <div className="space-y-3">
              <AnimatePresence>
                {apiKeys.map((key) => {
                  const keyInfo = AVAILABLE_API_KEYS.find(k => k.key === key.key_name);
                  return (
                    <motion.div
                      key={key.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-green-100 rounded-lg">
                          <Check className="w-4 h-4 text-green-600" />
                        </div>
                        <div>
                          <p className="font-medium">{keyInfo?.name || key.key_name}</p>
                          <p className="text-sm text-gray-500">{keyInfo?.provider}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge variant="outline" className="text-green-600 border-green-200 bg-green-50">
                          Active
                        </Badge>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteKey(key.id)}
                        >
                          <Trash2 className="w-4 h-4 text-red-500" />
                        </Button>
                      </div>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Platform Integrations */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ExternalLink className="w-5 h-5" />
            Social Platform Connections
          </CardTitle>
          <CardDescription>
            Connect your social accounts to enable posting and engagement management
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {PLATFORMS.map((platform) => {
              const integration = integrations.find(i => i.platform === platform.id);
              const isConnected = integration?.is_connected || false;

              return (
                <motion.div
                  key={platform.id}
                  whileHover={{ scale: 1.01 }}
                  className={`p-4 rounded-lg border ${
                    isConnected ? 'border-green-200 bg-green-50/50' : 'border-gray-200'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${platform.bgColor}`}>
                        <platform.icon className={`w-5 h-5 ${platform.color}`} />
                      </div>
                      <div>
                        <p className="font-medium">{platform.name}</p>
                        {isConnected && integration?.platform_username && (
                          <p className="text-sm text-gray-500">@{integration.platform_username}</p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {isConnected ? (
                        <>
                          <Badge className="bg-green-100 text-green-700">Connected</Badge>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDisconnectPlatform(platform.id)}
                          >
                            <X className="w-4 h-4" />
                          </Button>
                        </>
                      ) : (
                        <Button
                          size="sm"
                          onClick={() => handleConnectPlatform(platform.id)}
                        >
                          Connect
                        </Button>
                      )}
                    </div>
                  </div>

                  {isConnected && (
                    <div className="mt-4 pt-4 border-t border-gray-200 space-y-3">
                      <div className="flex items-center justify-between">
                        <Label htmlFor={`${platform.id}-auto-post`} className="text-sm cursor-pointer">
                          Auto-post after approval
                        </Label>
                        <Switch
                          id={`${platform.id}-auto-post`}
                          checked={integration?.auto_post_enabled || false}
                          onCheckedChange={(checked) =>
                            handleUpdateIntegration(platform.id, { auto_post_enabled: checked })
                          }
                        />
                      </div>
                      <div className="flex items-center justify-between">
                        <Label htmlFor={`${platform.id}-auto-reply`} className="text-sm cursor-pointer">
                          Auto-reply to comments
                        </Label>
                        <Switch
                          id={`${platform.id}-auto-reply`}
                          checked={integration?.auto_reply_enabled || false}
                          onCheckedChange={(checked) =>
                            handleUpdateIntegration(platform.id, { auto_reply_enabled: checked })
                          }
                        />
                      </div>
                      {integration?.auto_reply_enabled && (
                        <div className="flex items-center justify-between pl-4">
                          <Label htmlFor={`${platform.id}-low-risk`} className="text-sm cursor-pointer text-gray-500">
                            Only low-risk replies (thank-yous, etc.)
                          </Label>
                          <Switch
                            id={`${platform.id}-low-risk`}
                            checked={integration?.low_risk_auto_reply || false}
                            onCheckedChange={(checked) =>
                              handleUpdateIntegration(platform.id, { low_risk_auto_reply: checked })
                            }
                          />
                        </div>
                      )}
                    </div>
                  )}
                </motion.div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Add Key Dialog */}
      <Dialog open={showAddKeyDialog} onOpenChange={setShowAddKeyDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Add API Key</DialogTitle>
            <DialogDescription>
              Add your own API key to unlock premium AI capabilities
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Provider</Label>
              <Select value={selectedKeyType} onValueChange={setSelectedKeyType}>
                <SelectTrigger>
                  <SelectValue placeholder="Select provider" />
                </SelectTrigger>
                <SelectContent>
                  {AVAILABLE_API_KEYS.map((key) => (
                    <SelectItem key={key.key} value={key.key}>
                      <div className="flex flex-col">
                        <span>{key.name}</span>
                        <span className="text-xs text-gray-500">{key.description}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>API Key</Label>
              <div className="relative">
                <Input
                  type={showKeyValue ? 'text' : 'password'}
                  value={keyValue}
                  onChange={(e) => setKeyValue(e.target.value)}
                  placeholder="Enter your API key"
                />
                <Button
                  variant="ghost"
                  size="sm"
                  className="absolute right-2 top-1/2 -translate-y-1/2"
                  onClick={() => setShowKeyValue(!showKeyValue)}
                >
                  {showKeyValue ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </Button>
              </div>
            </div>
            <div className="flex items-start gap-2 p-3 bg-amber-50 rounded-lg">
              <AlertCircle className="w-4 h-4 text-amber-600 mt-0.5" />
              <p className="text-sm text-amber-700">
                Your API key is encrypted and stored securely. It will only be used for your content generation.
              </p>
            </div>
            <div className="flex justify-end gap-3">
              <Button variant="outline" onClick={() => setShowAddKeyDialog(false)}>
                Cancel
              </Button>
              <Button onClick={handleAddKey} disabled={isSaving}>
                {isSaving ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'Save Key'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
