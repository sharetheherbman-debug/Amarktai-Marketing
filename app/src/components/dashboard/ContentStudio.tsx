import { useState } from 'react';
import { 
  Wand2, 
  Image, 
  Video, 
  Type, 
  Mic,
  Sparkles,
  Download,
  Copy,
  RefreshCw,
  Palette,
  Music,
  Subtitles,
  Settings,
  Scissors,
  Layers,
  AlertTriangle
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { motion, AnimatePresence } from 'framer-motion';
import { containerVariants, itemVariants } from '@/lib/motion';
import { contentApi } from '@/lib/api';
import type { Platform } from '@/types';

interface GeneratedAsset {
  id: string;
  type: 'image' | 'video' | 'audio' | 'text';
  url?: string;
  content?: string;
  prompt: string;
  status: 'generating' | 'completed' | 'error';
  title?: string;
  caption?: string;
  errorMessage?: string;
  generationStatus?: string;
  generationMessage?: string;
}

export function ContentStudio() {
  const [prompt, setPrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedAssets, setGeneratedAssets] = useState<GeneratedAsset[]>([]);
  const [selectedStyle, setSelectedStyle] = useState('modern');
  const [intensity, setIntensity] = useState([50]);
  const [selectedPlatform, setSelectedPlatform] = useState<Platform>('instagram');
  const [webappId] = useState('default');

  const styles = [
    { id: 'modern', name: 'Modern', icon: Palette, color: 'from-blue-500 to-cyan-500' },
    { id: 'vintage', name: 'Vintage', icon: Image, color: 'from-amber-500 to-orange-500' },
    { id: 'minimal', name: 'Minimal', icon: Layers, color: 'from-slate-500 to-gray-500' },
    { id: 'bold', name: 'Bold', icon: Sparkles, color: 'from-purple-500 to-pink-500' },
    { id: 'corporate', name: 'Corporate', icon: Type, color: 'from-emerald-500 to-teal-500' },
  ];

  const platforms: { id: Platform; label: string }[] = [
    { id: 'instagram', label: 'Instagram' },
    { id: 'tiktok', label: 'TikTok' },
    { id: 'twitter', label: 'Twitter' },
    { id: 'facebook', label: 'Facebook' },
    { id: 'youtube', label: 'YouTube' },
    { id: 'linkedin', label: 'LinkedIn' },
  ];

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    
    setIsGenerating(true);
    
    const newAsset: GeneratedAsset = {
      id: Date.now().toString(),
      type: 'text',
      prompt,
      status: 'generating'
    };
    
    setGeneratedAssets(prev => [newAsset, ...prev]);

    try {
      const result = await contentApi.generate(webappId, selectedPlatform);
      setGeneratedAssets(prev =>
        prev.map(asset =>
          asset.id === newAsset.id
            ? {
                ...asset,
                status: 'completed' as const,
                content: result.caption,
                title: result.title,
                caption: result.caption,
                generationStatus: String(result.generationMetadata?.generation_status || "configured"),
                generationMessage: typeof result.generationMetadata?.message === "string" ? result.generationMetadata?.message : undefined,
              }
            : asset
        )
      );
    } catch (err) {
      setGeneratedAssets(prev =>
        prev.map(asset =>
          asset.id === newAsset.id
            ? {
                ...asset,
                status: 'error' as const,
                errorMessage: err instanceof Error ? err.message : 'Generation failed',
              }
            : asset
        )
      );
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div 
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-1 md:grid-cols-4 gap-4"
      >
        {[
          { icon: Image, label: 'Images Generated', value: '1,247', color: 'text-pink-400', bg: 'bg-pink-500/20' },
          { icon: Video, label: 'Videos Created', value: '89', color: 'text-purple-400', bg: 'bg-purple-500/20' },
          { icon: Mic, label: 'Voiceovers', value: '234', color: 'text-blue-400', bg: 'bg-blue-500/20' },
          { icon: Type, label: 'Captions', value: '3,456', color: 'text-green-400', bg: 'bg-green-500/20' },
        ].map((stat, i) => (
          <motion.div key={i} variants={itemVariants}>
            <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700/50">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-slate-400 text-sm">{stat.label}</p>
                    <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
                  </div>
                  <div className={`p-3 rounded-xl ${stat.bg}`}>
                    <stat.icon className={`w-5 h-5 ${stat.color}`} />
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Generation Panel */}
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="lg:col-span-2 space-y-4"
        >
          <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700/50">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Wand2 className="w-5 h-5 text-purple-400" />
                AI Content Generator
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Prompt Input */}
              <div className="space-y-2">
                <label className="text-sm text-slate-400">What would you like to create?</label>
                <Textarea
                  placeholder="Describe your content idea... (e.g., 'A modern tech product showcase with blue gradients and floating elements')"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  className="min-h-[100px] bg-slate-800/50 border-slate-700 resize-none"
                />
              </div>

              {/* Platform Selection */}
              <div className="space-y-2">
                <label className="text-sm text-slate-400">Target Platform</label>
                <div className="flex flex-wrap gap-2">
                  {platforms.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => setSelectedPlatform(p.id)}
                      className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                        selectedPlatform === p.id
                          ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                          : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-slate-700/50'
                      }`}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Style Selection */}
              <div className="space-y-2">
                <label className="text-sm text-slate-400">Visual Style</label>
                <div className="flex flex-wrap gap-2">
                  {styles.map((style) => (
                    <motion.button
                      key={style.id}
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => setSelectedStyle(style.id)}
                      className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-all ${
                        selectedStyle === style.id
                          ? `bg-gradient-to-r ${style.color} border-transparent text-white`
                          : 'bg-slate-800/50 border-slate-700 text-slate-400 hover:border-slate-600'
                      }`}
                    >
                      <style.icon className="w-4 h-4" />
                      {style.name}
                    </motion.button>
                  ))}
                </div>
              </div>

              {/* Settings */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm text-slate-400 flex items-center justify-between">
                    Creativity Level
                    <span className="text-slate-300">{intensity[0]}%</span>
                  </label>
                  <Slider 
                    value={intensity} 
                    onValueChange={setIntensity}
                    max={100}
                    step={10}
                    className="w-full"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm text-slate-400">Options</label>
                  <div className="flex gap-4">
                    <div className="flex items-center gap-2">
                      <Switch id="hd" defaultChecked className="data-[state=checked]:bg-purple-500" />
                      <label htmlFor="hd" className="text-sm text-slate-300">HD Quality</label>
                    </div>
                    <div className="flex items-center gap-2">
                      <Switch id="watermark" className="data-[state=checked]:bg-purple-500" />
                      <label htmlFor="watermark" className="text-sm text-slate-300">No Watermark</label>
                    </div>
                  </div>
                </div>
              </div>

              {/* Generate Button */}
              <Button 
                onClick={handleGenerate}
                disabled={isGenerating || !prompt.trim()}
                className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
              >
                {isGenerating ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 mr-2" />
                    Generate Content
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Recent Generations */}
          <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700/50">
            <CardHeader>
              <CardTitle className="text-lg">Recent Generations</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <AnimatePresence>
                  {generatedAssets.map((asset) => (
                    <motion.div
                      key={asset.id}
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.9 }}
                      className="relative group"
                    >
                      <div className="p-4 bg-slate-800 rounded-lg overflow-hidden min-h-[120px]">
                        {asset.status === 'generating' ? (
                          <div className="w-full h-full flex items-center justify-center">
                            <div className="text-center">
                              <RefreshCw className="w-8 h-8 text-purple-400 animate-spin mx-auto mb-2" />
                              <p className="text-sm text-slate-400">Generating...</p>
                            </div>
                          </div>
                        ) : asset.status === 'error' ? (
                          <div className="w-full h-full flex items-center justify-center">
                            <div className="text-center">
                              <AlertTriangle className="w-8 h-8 text-yellow-400 mx-auto mb-2" />
                              <p className="text-sm text-red-400">{asset.errorMessage || 'Generation failed'}</p>
                            </div>
                          </div>
                        ) : (
                          <div>
                            {asset.title && (
                              <h4 className="font-medium text-slate-200 mb-2">{asset.title}</h4>
                            )}
                            <p className="text-sm text-slate-300 line-clamp-4">{asset.caption || asset.content}</p>
                            {asset.generationStatus === 'not_configured' && (
                              <p className="text-xs text-amber-300 mt-2">{asset.generationMessage || 'GENX_API_KEY is not configured. Output is degraded.'}</p>
                            )}
                          </div>
                        )}
                      </div>
                      
                      {asset.status === 'completed' && (
                        <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity rounded-lg flex items-center justify-center gap-2">
                          <Button size="sm" variant="secondary">
                            <Download className="w-4 h-4" />
                          </Button>
                          <Button size="sm" variant="secondary">
                            <Copy className="w-4 h-4" />
                          </Button>
                        </div>
                      )}
                    </motion.div>
                  ))}
                </AnimatePresence>

                {/* Placeholder */}
                {generatedAssets.length === 0 && (
                  <div className="aspect-video bg-slate-800/50 rounded-lg border-2 border-dashed border-slate-700 flex items-center justify-center">
                    <p className="text-slate-500 text-sm">Your generations will appear here</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Tools Panel */}
        <motion.div 
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="space-y-4"
        >
          <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700/50">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Settings className="w-5 h-5 text-blue-400" />
                Quick Tools
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {[
                { icon: Type, name: 'Caption Generator', desc: 'AI-powered captions', color: 'text-green-400', bg: 'bg-green-500/20' },
                { icon: Subtitles, name: 'Subtitle Creator', desc: 'Auto-generate subtitles', color: 'text-yellow-400', bg: 'bg-yellow-500/20' },
                { icon: Music, name: 'Background Music', desc: 'Royalty-free tracks', color: 'text-pink-400', bg: 'bg-pink-500/20' },
                { icon: Scissors, name: 'Video Trimmer', desc: 'Quick video edits', color: 'text-purple-400', bg: 'bg-purple-500/20' },
                { icon: Mic, name: 'Voice Over', desc: 'AI voice synthesis', color: 'text-blue-400', bg: 'bg-blue-500/20' },
              ].map((tool) => (
                <motion.button
                  key={tool.name}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="w-full flex items-center gap-3 p-3 bg-slate-800/50 rounded-lg hover:bg-slate-800 transition-colors text-left"
                >
                  <div className={`p-2 rounded-lg ${tool.bg}`}>
                    <tool.icon className={`w-5 h-5 ${tool.color}`} />
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-slate-200 text-sm">{tool.name}</p>
                    <p className="text-xs text-slate-400">{tool.desc}</p>
                  </div>
                </motion.button>
              ))}
            </CardContent>
          </Card>

          {/* Templates */}
          <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700/50">
            <CardHeader>
              <CardTitle className="text-lg">Popular Templates</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {[
                { name: 'Product Showcase', uses: '2.4K uses', image: 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=200&h=120&fit=crop' },
                { name: 'Testimonial Video', uses: '1.8K uses', image: 'https://images.unsplash.com/photo-1551836022-d5d88e9218df?w=200&h=120&fit=crop' },
                { name: 'Announcement Post', uses: '3.2K uses', image: 'https://images.unsplash.com/photo-1557804506-669a67965ba0?w=200&h=120&fit=crop' },
              ].map((template) => (
                <motion.div
                  key={template.name}
                  whileHover={{ scale: 1.02 }}
                  className="relative overflow-hidden rounded-lg cursor-pointer group"
                >
                  <img 
                    src={template.image} 
                    alt={template.name}
                    className="w-full h-20 object-cover"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent flex items-end p-3">
                    <div>
                      <p className="font-medium text-white text-sm">{template.name}</p>
                      <p className="text-xs text-slate-300">{template.uses}</p>
                    </div>
                  </div>
                  <div className="absolute inset-0 bg-purple-500/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <Badge className="bg-purple-500 text-white">
                      <Sparkles className="w-3 h-3 mr-1" /> Use Template
                    </Badge>
                  </div>
                </motion.div>
              ))}
            </CardContent>
          </Card>

          {/* AI Tips */}
          <Card className="bg-gradient-to-br from-purple-900/20 to-pink-900/20 border-purple-500/30">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-purple-500/20 rounded-lg">
                  <Sparkles className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <h4 className="font-medium text-slate-200 mb-1">Pro Tip</h4>
                  <p className="text-sm text-slate-400">
                    Use specific color names and lighting descriptions for better results. Try "neon blue lighting with soft shadows."
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}
