import React, { useState } from 'react'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import SlotMachine from './extensions/SlotMachine/SlotMachineNode'
import ScryingGlass from '../scrying-glass/ScryingGlass'
import TopBar from '../layout/TopBar'
import LeftSidebar from '../layout/LeftSidebar'
import { Bold, Italic, Underline, Search } from 'lucide-react'

const GrimoireEditor = ({ onBack }: { onBack: () => void }) => {
  const [activeMeta, setActiveMeta] = useState<any>(null)

  const editor = useEditor({
    extensions: [
      StarterKit,
      SlotMachine,
    ],
    content: `
      <h2>Chapter 1</h2>
      <p>In the choleric summer of 1789, when the streets of Paris were the veins of a living beast...</p>
      <slot-machine 
        selectedIndex="0" 
        variants='[
          {"label": "Sensory", "text": "The stink of open sewers mingled with the sweat of the mob.", "style_tag": "sensory"},
          {"label": "Action", "text": "Lucien de Valois awoke to the sound of breaking glass.", "style_tag": "action"}
        ]'
        meta_info='{"scrying_glass": {"rag_hits": ["Paris", "Lucien"], "strategy_explanation": "Historical setting establishment."}}'
      ></slot-machine>
    `,
    onSelectionUpdate: ({ editor }) => {
      const { $from } = editor.state.selection
      const node = $from.node()
      if (node.type.name === 'slotMachine') {
        setActiveMeta(node.attrs.meta_info)
      } else {
        setActiveMeta(null)
      }
    },
  })

  return (
    <div className="flex flex-col h-screen bg-gray-50 overflow-hidden">
      <TopBar onBack={onBack} />
      
      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar */}
        <LeftSidebar projectTitle="My First Project" />

        {/* Main Editor Area */}
        <div className="flex-1 flex flex-col relative bg-white">
          {/* Floating Toolbar (Mock) */}
          <div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-white shadow-md border border-gray-200 rounded-lg px-2 py-1.5 flex gap-1 z-10">
            <button className="p-1.5 hover:bg-gray-100 rounded text-gray-600"><Search size={16}/></button>
            <div className="w-px h-4 bg-gray-200 my-auto"></div>
            <button className="p-1.5 hover:bg-gray-100 rounded text-gray-600"><Bold size={16}/></button>
            <button className="p-1.5 hover:bg-gray-100 rounded text-gray-600"><Italic size={16}/></button>
            <button className="p-1.5 hover:bg-gray-100 rounded text-gray-600"><Underline size={16}/></button>
          </div>

          <div className="flex-1 overflow-y-auto px-12 py-8 scroll-smooth">
            <div className="max-w-2xl mx-auto min-h-[800px] bg-white">
              <EditorContent editor={editor} className="outline-none typography prose-lg" />
            </div>
          </div>
        </div>

        {/* Right Sidebar */}
        <ScryingGlass meta={activeMeta} />
      </div>
    </div>
  )
}

export default GrimoireEditor