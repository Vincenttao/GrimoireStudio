import React from 'react'
import { Sparkles, MessageSquare, History, Wand2 } from 'lucide-react'

interface ScryingGlassProps {
  meta: any
}

const ScryingGlass: React.FC<ScryingGlassProps> = ({ meta }) => {
  const data = meta?.scrying_glass

  return (
    <div className="w-80 bg-gray-50 h-full flex flex-col border-l border-gray-200">
      {/* Tabs */}
      <div className="flex p-2 gap-2">
        <button className="flex-1 py-1.5 bg-white shadow-sm rounded text-xs font-medium text-gray-800 flex items-center justify-center gap-1">
          <History size={12} /> History
        </button>
        <button className="flex-1 py-1.5 text-xs font-medium text-gray-500 hover:text-gray-800 flex items-center justify-center gap-1">
          <MessageSquare size={12} /> Chat
        </button>
      </div>

      {/* Cards Stream */}
      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        {/* Suggestion Card (Mock) */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-100 p-4 hover:shadow-md transition-shadow cursor-pointer">
          <div className="flex items-center gap-2 mb-2 text-purple-600">
            <Wand2 size={14} />
            <span className="text-xs font-bold uppercase tracking-wider">Write Suggestion</span>
          </div>
          <p className="text-sm text-gray-700 leading-relaxed italic">
            ...t danced like miniature revolutionaries in the stifling air.
          </p>
        </div>

        {/* Rewrite Card (Mock) */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-100 p-4 hover:shadow-md transition-shadow cursor-pointer">
          <div className="flex items-center gap-2 mb-2 text-indigo-600">
            <Sparkles size={14} />
            <span className="text-xs font-bold uppercase tracking-wider">Rewrite</span>
          </div>
          <p className="text-sm text-gray-700 leading-relaxed italic">
            ...olent clarity. The sunlight sliced the slats of the battered...
          </p>
        </div>

        {/* Dynamic RAG Content */}
        {data && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-100 p-4 animate-in fade-in slide-in-from-right-4">
            <div className="flex items-center gap-2 mb-2 text-teal-600">
              <Sparkles size={14} />
              <span className="text-xs font-bold uppercase tracking-wider">Grimoire Insight</span>
            </div>
            <p className="text-xs text-gray-500 mb-2">{data.strategy_explanation}</p>
            <div className="flex flex-wrap gap-1">
              {data.rag_hits?.map((hit: string, i: number) => (
                <span key={i} className="px-1.5 py-0.5 bg-teal-50 text-teal-700 rounded text-[10px] border border-teal-100">
                  {hit}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer Actions */}
      <div className="p-3 border-t border-gray-200 bg-gray-50 space-y-2">
        <div className="h-1 bg-gray-200 rounded-full overflow-hidden">
          <div className="h-full bg-purple-300 w-3/4"></div>
        </div>
        <div className="text-[10px] text-center text-gray-400">0 credits left</div>
        
        <div className="flex gap-2 mt-2">
          <button className="flex-1 py-2 border border-purple-600 text-purple-600 rounded-md text-sm font-medium hover:bg-purple-50">
            Support
          </button>
          <button className="flex-1 py-2 bg-purple-600 text-white rounded-md text-sm font-medium hover:bg-purple-700">
            Upgrade
          </button>
        </div>
      </div>
    </div>
  )
}

export default ScryingGlass
