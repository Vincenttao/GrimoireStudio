import React from 'react';
import { Plus, Upload, Book, Trash2, ChevronsLeft, Layout, FileText } from 'lucide-react';

const LeftSidebar = ({ projectTitle }: { projectTitle: string }) => {
  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col h-full">
      {/* Project Header */}
      <div className="p-4 flex items-center justify-between">
        <h2 className="font-medium text-gray-900 truncate pr-2">{projectTitle}</h2>
        <button className="text-gray-400 hover:text-gray-600">
          <ChevronsLeft size={18} />
        </button>
      </div>

      {/* Action Buttons */}
      <div className="px-4 pb-4 flex gap-2">
        <button className="flex-1 flex items-center justify-center gap-1.5 py-1.5 border border-gray-200 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50">
          <Plus size={16} /> New
        </button>
        <button className="flex-1 flex items-center justify-center gap-1.5 py-1.5 border border-gray-200 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50">
          <Upload size={16} /> Import
        </button>
      </div>

      {/* Chapter List */}
      <div className="flex-1 overflow-y-auto px-2 space-y-0.5">
        <div className="flex items-center gap-2 px-3 py-2 bg-purple-50 text-purple-700 rounded-md text-sm font-medium">
          <FileText size={16} />
          Chapter 1
        </div>
        {/* Mock additional chapters */}
        {[2, 3].map(i => (
          <div key={i} className="flex items-center gap-2 px-3 py-2 text-gray-600 hover:bg-gray-50 rounded-md text-sm cursor-pointer">
            <FileText size={16} />
            Chapter {i}
          </div>
        ))}
      </div>

      {/* Bottom Actions */}
      <div className="p-4 space-y-2 border-t border-gray-100">
        <button className="flex items-center justify-between w-full px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 hover:border-purple-300 group">
          <div className="flex items-center gap-2">
            <Book size={16} className="text-purple-600" />
            <span className="font-medium">Story Bible</span>
          </div>
          <div className="w-8 h-4 bg-gray-200 rounded-full relative">
            <div className="w-4 h-4 bg-white rounded-full shadow-sm absolute left-0 border border-gray-300"></div>
          </div>
        </button>
        
        <button className="flex items-center gap-2 px-3 py-2 text-gray-400 hover:text-red-500 text-sm w-full">
          <Trash2 size={16} />
          Trash
        </button>
      </div>
    </div>
  );
};

export default LeftSidebar;
