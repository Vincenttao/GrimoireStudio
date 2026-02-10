import React, { useEffect, useState } from 'react'
import { NodeViewWrapper, NodeViewContent } from '@tiptap/react'
import { ChevronRight, ChevronLeft, Sparkles } from 'lucide-react'
import { cn } from '../../../../lib/utils'

const SlotMachineView = ({ node, updateAttributes, selected }: any) => {
  const { variants, selectedIndex, isDirty } = node.attrs
  const [localIndex, setLocalIndex] = useState(selectedIndex)

  const currentVariant = variants[localIndex] || { text: 'Empty Slot' }

  const handleNext = () => {
    const nextIndex = (localIndex + 1) % variants.length
    setLocalIndex(nextIndex)
    updateAttributes({ 
      selectedIndex: nextIndex,
      isDirty: true 
    })
  }

  const handlePrev = () => {
    const prevIndex = (localIndex - 1 + variants.length) % variants.length
    setLocalIndex(prevIndex)
    updateAttributes({ 
      selectedIndex: prevIndex,
      isDirty: true 
    })
  }

  // Commitment Logic (SPEC 8): Trigger when user leaves the block
  useEffect(() => {
    if (!selected && isDirty) {
      console.log('Leaving block, committing variant:', currentVariant.text)
      // Here we would call triggerSmoothing(currentVariant)
      updateAttributes({ 
        isDirty: false,
        content_snapshot: currentVariant.text // Atomic Sync
      })
    }
  }, [selected, isDirty, currentVariant, updateAttributes])

  return (
    <NodeViewWrapper className="relative my-4 group border-l-2 border-transparent hover:border-purple-400 pl-4 transition-all">
      <div className="flex items-center gap-2 mb-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <div className="flex items-center bg-gray-100 rounded p-1 border">
          <button onClick={handlePrev} className="hover:bg-gray-200 rounded p-0.5">
            <ChevronLeft size={14} />
          </button>
          <span className="text-[10px] font-mono px-2 min-w-[3rem] text-center">
            {localIndex + 1} / {variants.length}
          </span>
          <button onClick={handleNext} className="hover:bg-gray-200 rounded p-0.5">
            <ChevronRight size={14} />
          </button>
        </div>
        <div className="text-[10px] uppercase tracking-wider text-purple-600 font-bold flex items-center gap-1">
          <Sparkles size={10} />
          {currentVariant.label || 'AI Variant'}
        </div>
      </div>
      
      <div className={cn(
        "prose prose-sm max-w-none text-gray-800 leading-relaxed",
        isDirty && "text-purple-900 font-medium"
      )}>
        {currentVariant.text}
      </div>

      {/* Hidden content for Tiptap to sync with */}
      <NodeViewContent className="hidden" />
    </NodeViewWrapper>
  )
}

export default SlotMachineView
