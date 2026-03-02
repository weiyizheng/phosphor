# Phosphor UI Redesign Implementation Plan

## Goal Description
Redesign the UI of the Phosphor CLI audio analyzer to have a modern, "beautiful" aesthetic inspired by `btop`. This involves transitioning from standard terminal ASCII boxes and simple braille particles to rounded box layouts, block-character based graphs, and introducing dynamic neon/gradient colors.

## Proposed Changes
### `vfd` (Core Renderer & Colors)
#### [MODIFY] [renderer.py](file:///Users/weiyizheng/Projects/phosphor/src/vfd/renderer.py)
- Replace the standard `win.box()` call in `_draw_panel` with a custom box-drawing algorithm that uses rounded border characters (`╭`, `─`, `╮`, `│`, `╰`, `╯`).
- Format panel title to have a cleaner separation from the top border.

#### [MODIFY] [vfd_colors.py](file:///Users/weiyizheng/Projects/phosphor/src/vfd/vfd_colors.py)
- Introduce a new color theme named `btop` and make it visually distinct (e.g., purple/cyan/magenta hues akin to standard dracula/neon themes). 

### `vfd/meters` (Graph Components)
#### [MODIFY] [spectrum.py](file:///Users/weiyizheng/Projects/phosphor/src/vfd/meters/spectrum.py)
- Replace the simple braille particles (`⠄`, `⣤`, `⣿`) with a vertical fractional block character set (` `, `▂`, `▃`, `▄`, `▅`, `▆`, `▇`, `█`) to give it a solid, vibrant look akin to `btop`'s block meters, or refine the braille usage.

#### [MODIFY] [vu.py](file:///Users/weiyizheng/Projects/phosphor/src/vfd/meters/vu.py)
- Upgrade horizontal segmented meters to use horizontal fractional block characters (`▏`, `▎`, `▍`, `▌`, `▋`, `▊`, `▉`, `█`).

#### [MODIFY] [rms.py](file:///Users/weiyizheng/Projects/phosphor/src/vfd/meters/rms.py)
- Upgrade horizontal meters to use horizontal block characters.

#### [MODIFY] [peak.py](file:///Users/weiyizheng/Projects/phosphor/src/vfd/meters/peak.py)
- Upgrade both vertical and horizontal peak meters to use appropriate fractional block characters.

#### [MODIFY] [lufs.py](file:///Users/weiyizheng/Projects/phosphor/src/vfd/meters/lufs.py)
- Replace the ASCII sparkline characters (` .:-=+*#%@`) with vertical block characters (` ▂▃▄▅▆▇█`) for a much smoother history graph.

## Verification Plan
### Automated Tests
- Run `pytest` if a `tests/` directory exists to ensure rendering logic doesn't crash on mocked inputs.

### Manual Verification
- Ask the user to run the tool locally: `python3 -m vfd --layout dashboard` and `python3 -m vfd --layout classic`.
- Visually inspect the changes to ensure:
  1. Box borders have rounded corners rather than the default `+` and `-`.
  2. The spectrum and LUFS graphs render smoothly using the block characters.
  3. The color palette looks more dynamic and modern.
