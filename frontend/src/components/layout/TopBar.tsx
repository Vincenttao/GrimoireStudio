import React from 'react';
import { ArrowLeft, Share, HelpCircle, Settings, ChevronDown, Sparkles, PenTool, Lightbulb, Zap } from 'lucide-react';

const TopBar = ({ onBack }: { onBack: () => void }) => {
  return (
    <div className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-4 shrink-0">
      {/* Left: Back & Modes */}
      <div className="flex items-center gap-4">
        <button onClick={onBack} className="flex items-center gap-1 text-sm font-medium text-gray-700 hover:text-black">
          <ArrowLeft size={16} />
          Back
        </button>

        <div className="h-6 w-px bg-gray-200 mx-2"></div>

        <div className="flex bg-gray-100 p-1 rounded-lg">
          <button className="flex items-center gap-1.5 px-3 py-1 bg-white shadow-sm rounded-md text-sm font-medium text-gray-800">
            <PenTool size={14} /> Write
          </button>
          <button className="flex items-center gap-1.5 px-3 py-1 text-sm font-medium text-gray-500 hover:text-gray-800">
            <Sparkles size={14} /> Rewrite
          </button>
          <button className="flex items-center gap-1.5 px-3 py-1 text-sm font-medium text-gray-500 hover:text-gray-800">
            <Zap size={14} /> Describe
          </button>
          <button className="flex items-center gap-1.5 px-3 py-1 text-sm font-medium text-gray-500 hover:text-gray-800">
            <Lightbulb size={14} /> Brainstorm
          </button>
        </div>

        <button className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 rounded-md text-sm font-medium text-gray-600 hover:bg-gray-200">
          <Sparkles size={14} /> More Tools <ChevronDown size={14} />
        </button>
      </div>

      {/* Right: Meta & Actions */}
      <div className="flex items-center gap-4">
        <div className="text-xs text-gray-500 font-mono">
          Words: 210 <span className="mx-2 text-gray-300">|</span> Saving...
        </div>
        
        <div className="flex items-center gap-3 text-gray-600">
          <button><Share size={18} /></button>
          <button><HelpCircle size={18} /></button>
          <button><Settings size={18} /></button>
        </div>
      </div>
    </div>
  );
};

export default TopBar;
