import React, { useEffect, useState } from 'react';
import { Plus, Upload, Search, HelpCircle, Settings, MoreHorizontal, X } from 'lucide-react';
import { GradientBackground } from '../layout/GradientBackground';
import { useAppStore } from '../../store/appStore';

const Dashboard = ({ onSelectProject }: { onSelectProject: (id: number) => void }) => {
  const user = useAppStore((state) => state.user);
  // Mock projects for now
  const projects = [
    { id: 1, title: 'My First Project', words: 210, daysAgo: 1 }
  ];

  return (
    <GradientBackground>
      {/* Top Nav */}
      <nav className="flex items-center justify-between px-6 py-4">
        <div className="flex items-center gap-6">
          <button className="flex items-center gap-2 text-gray-800 font-medium hover:text-black">
            <Plus size={20} />
            New
          </button>
          <button className="flex items-center gap-2 text-gray-800 font-medium hover:text-black">
            <Upload size={20} />
            Import Novel
          </button>
        </div>
        
        <div className="absolute left-1/2 transform -translate-x-1/2 font-serif text-2xl font-bold text-gray-900 tracking-tight">
          sudo<span className="italic font-normal">write</span>
        </div>

        <div className="flex items-center gap-4 text-gray-700">
          <button><Search size={20} /></button>
          <button><HelpCircle size={20} /></button>
          <button><Settings size={20} /></button>
          {user && (
            <div className="w-8 h-8 bg-purple-600 rounded-full flex items-center justify-center text-white text-xs font-bold">
              {user.email[0].toUpperCase()}
            </div>
          )}
        </div>
      </nav>

      {/* Main Content */}
      <div className="flex items-center justify-center h-[calc(100vh-80px)] gap-8">
        {/* Project Card */}
        {projects.map(project => (
          <div 
            key={project.id}
            onClick={() => onSelectProject(project.id)}
            className="w-64 h-80 bg-white rounded-lg shadow-sm hover:shadow-md transition-shadow cursor-pointer p-6 flex flex-col relative group"
          >
            <button className="absolute top-4 right-4 text-gray-400 hover:text-gray-600">
              <MoreHorizontal size={20} />
            </button>
            
            <div className="flex-1 flex items-center justify-center text-center">
              <h3 className="font-serif text-3xl text-gray-800 leading-tight">
                {project.title}
              </h3>
            </div>
            
            <div className="text-center text-xs text-gray-400 font-medium uppercase tracking-wider">
              {project.words} words<br />
              {project.daysAgo}d
            </div>
          </div>
        ))}

        {/* Resources Card (Static) */}
        <div className="w-64 h-80 bg-white rounded-lg shadow-sm p-6 flex flex-col relative rotate-3 hover:rotate-0 transition-transform duration-300">
          <button className="absolute top-4 right-4 text-gray-400">
            <X size={16} />
          </button>
          <div className="text-center mb-6 mt-4">
            <h3 className="font-serif text-2xl text-gray-800">Writer-made<br/>resources</h3>
          </div>
          <div className="space-y-3 flex-1">
            {['Browse Live Classes', 'Join Our Community', 'Learn On YouTube', 'Read The Docs'].map(item => (
              <button key={item} className="w-full py-2 px-3 border border-gray-200 rounded text-sm text-gray-600 hover:bg-gray-50 transition-colors">
                {item}
              </button>
            ))}
          </div>
        </div>
      </div>
    </GradientBackground>
  );
};

export default Dashboard;
