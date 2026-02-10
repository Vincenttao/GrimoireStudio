import { Node, mergeAttributes } from '@tiptap/core'
import { ReactNodeViewRenderer } from '@tiptap/react'
import SlotMachineView from './SlotMachineView'

export default Node.create({
  name: 'slotMachine',
  group: 'block',
  content: 'inline*',
  draggable: true,

  addAttributes() {
    return {
      variants: {
        default: [],
      },
      selectedIndex: {
        default: 0,
      },
      meta_info: {
        default: {},
      },
      isDirty: {
        default: false,
      }
    }
  },

  parseHTML() {
    return [
      {
        tag: 'slot-machine',
      },
    ]
  },

  renderHTML({ HTMLAttributes }) {
    return ['slot-machine', mergeAttributes(HTMLAttributes), 0]
  },

  addNodeView() {
    return ReactNodeViewRenderer(SlotMachineView)
  },
})
