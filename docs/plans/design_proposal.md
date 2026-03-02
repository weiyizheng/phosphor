# Design Proposal: Phosphor "Btop Edition"

## 🎨 Inspiration
The goal is to move from a classic, "dot-matrix" VFD look to a modern, high-density dashboard aesthetic inspired by [btop](https://github.com/aristocratos/btop). This involves a shift from ASCII/Braille particles to solid block characters and more sophisticated layout elements.

## ✨ Key Design Elements

### 1. Rounded Borders
- **Current**: Standard `+`, `-`, `|` or the `win.box()` default which uses sharp corners.
- **Proposed**: Custom rounded corners (`╭`, `╮`, `╰`, `╯`) with smooth horizontal (`─`) and vertical (`│`) lines. This instantly makes the CLI feel more premium and modern.

### 2. Fractional Block Meters
- **Current**: Simple braille particles (`⠄`, `⣤`, `⣿`) which look "dotted".
- **Proposed**: Use Unicode Block Elements.
  - **Vertical (Spectrum/LUFS)**: ` `, `▂`, `▃`, `▄`, `▅`, `▆`, `▇`, `█`. This allows for much smoother gradients and a "solid" bar look.
  - **Horizontal (VU/RMS/Peak)**: `▏`, `▎`, `▍`, `▌`, `▋`, `▊`, `▉`, `█`. This provides 8x more horizontal resolution than standard characters.

### 3. "Btop" Color Palette
- **Primary**: Neon Purple / Magenta (for mid-range signals).
- **Secondary**: Cyan / Bright Blue (for low-level signals).
- **Accents**: Neon Green / Yellow (for warning transitions).
- **Critical**: Bright Red (for clipping).
- **Background**: Deep Grey/Black (standard terminal BG).

### 4. Layout Improvements
- **Dashboard View**: Ensuring meters are aligned with consistent padding.
- **Micro-Animations**: Refining the "ballistic" decay rates to feel more snappy and realistic, matching the high refresh rate of modern terminals.

## 🚀 Vision
By the end of this redesign, **Phosphor** will look like a state-of-the-art system monitoring tool, but for audio. It will fit perfectly into a professional "rice" setup or a music producer's terminal.
