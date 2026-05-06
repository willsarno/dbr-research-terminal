# Research Terminal Design System

## Purpose

This document defines the shared frontend design foundation for Research Terminal. It is intended to guide UI work in v0 without changing backend logic, data contracts, financial calculations, or application behavior.

The target product character is:

- institutional
- dark mode only
- information-dense but controlled
- modern terminal-like, not retro terminal-like
- technically credible
- visually calm and low-fatigue

## Color Palette

### Core backgrounds

- `--dbr-bg`: `#020617`
  - App-level background
- `--dbr-surface`: `#08111F`
  - Base content surface
- `--dbr-surface-elevated`: `#0B1220`
  - Cards, panels, chart containers
- `--dbr-surface-panel`: `#0D1628`
  - Insight bars, alerts, layered emphasis
- `--dbr-surface-overlay`: `rgba(11, 18, 32, 0.92)`
  - Overlays and translucent surfaces

### Borders

- `--dbr-border`: `#18263A`
  - Standard subtle border
- `--dbr-border-strong`: `#22324A`
  - Active or hover border

### Text

- `--dbr-text`: `#E2E8F0`
  - Primary high-contrast text
- `--dbr-muted`: `#94A3B8`
  - Secondary text
- `--dbr-muted-soft`: `#64748B`
  - Tertiary text and low-priority labels

### Accent and status

- `--dbr-accent`: `#3B82F6`
  - Primary interactive accent
- `--dbr-accent-soft`: `rgba(59, 130, 246, 0.16)`
  - Accent fill
- `--dbr-accent-glow`: `rgba(59, 130, 246, 0.12)`
  - Focus glow
- `--dbr-positive`: `#10B981`
  - Positive trend or gain
- `--dbr-negative`: `#EF4444`
  - Negative trend or loss
- `--dbr-warning`: `#F59E0B`
  - Caution and data-quality warnings

## Typography System

### Typeface approach

Use a clean modern sans stack:

- `Inter`
- `ui-sans-serif`
- `system-ui`
- `Segoe UI`

No decorative or novelty fonts.

### Hierarchy

- Marketing / landing title:
  - 36–42px
  - weight 700
  - tight line-height
- Page titles:
  - 28–32px
  - weight 700
- Section titles:
  - 20–24px
  - weight 650
- Card metric values:
  - 22–26px
  - weight 700
- Card labels / metadata:
  - 11–12px
  - uppercase
  - letter spacing around `0.08em`
- Body text:
  - 14–15px
  - line-height around `1.5–1.58`
- Secondary copy:
  - muted slate tone
  - slightly smaller than body text

### Tone

- Avoid loud headline styling
- Prioritize scanability over marketing emphasis
- Keep typography crisp and restrained

## Spacing Rules

### Layout widths

- Main app max-width: around `1360px`
- Keep content centered and readable
- Avoid excessive full-bleed layouts unless needed for dense tables or charts

### Vertical rhythm

- Major section spacing: `32px`
- Card grid gap: `16px`
- Toolbar-to-results gap: `20–24px`
- Compact chart stack spacing: `12–16px`

### Card internals

- Standard internal padding: `18–22px`
- Metric cards may be slightly tighter when data-dense
- Avoid large empty interiors

## Border Radius and Depth

### Radius

- Small: `10px`
- Medium: `14px`
- Large: `18px`

Use medium radius for most application surfaces.

### Shadows

- Shadows should be soft and low-contrast
- Use depth to separate surfaces, not to create glow-heavy decoration
- Prefer subtle navy-black diffusion rather than bright colored shadows

## Motion / Animation Philosophy

- Fast and subtle only
- Use motion to indicate focus, hover, or activation
- No dramatic transitions
- Recommended duration:
  - 140ms for hover/focus
  - 200ms for card/background/border transitions

## Card Philosophy

Cards should feel like analytical modules, not marketing tiles.

### Standard card behavior

- dark elevated surface
- subtle border
- minimal top or left accent only when semantically useful
- compact content flow
- consistent spacing inside the grid

### KPI panels

- small uppercase label
- bold numeric value
- muted context line
- consistent height across a row

### AI insight / narrative panels

- use soft panel background
- left accent border in primary blue
- compact copy blocks
- visually distinct from metric cards, but same system family

## Table Philosophy

- Tables are a data tool, not a decorative component
- Keep row density moderately tight
- Use muted headers
- Avoid thick row separators
- Use borders only where they improve scannability
- Preserve horizontal clarity for financial metrics

For comparison tables:

- numeric alignment should be visually consistent
- formatted values should remain concise
- missing values should not dominate the visual hierarchy

## Dashboard Philosophy

The dashboard should feel like an internal investment research workspace:

- calm
- information-rich
- structured into modules
- fast to scan

### Principles

- primary tasks should appear above secondary analysis
- use visual weight to guide interpretation
- prefer grouped modules over scattered widgets
- charts and tables should feel integrated into one analytical system

## UI Density Rules

- Dense, but never cramped
- Prefer tighter spacing over oversized decorative whitespace
- Use compact toolbars for inputs and filters
- Keep alerts concise and non-disruptive
- Maintain breathing room between major analytical blocks

## Chart Styling Rules

### Container treatment

- charts should live inside elevated dark containers
- use subtle border and soft depth
- no bright glows
- no consumer-dashboard gradients

### Plot styling

- paper background: `#020617`
- plot background: `#0B1220`
- grid lines: subtle slate tone
- axis labels: muted slate
- title: bright but restrained
- legend: horizontal when possible, placed above data

### Color behavior

Use restrained colors:

- blue for primary series
- green for constructive/positive series
- red for negative/risk series
- amber only for warnings or caution
- slate/teal for secondary analytical context

Avoid:

- neon cyan overuse
- bright purple emphasis
- rainbow color sets
- overly saturated pie/donut palettes

## Navigation and Shell

- Sidebar should be compact and branded, not noisy
- Branding should be present but understated
- Navigation labels should remain short and operational
- Global shell chrome should be reduced wherever safe

## Reusable Utility Philosophy

Shared primitives should cover:

- surfaces
- elevated cards
- alerts
- insight bars
- chart shells
- dense metric grids
- compact settings toolbars

These utilities should be reusable across:

- company research
- peer comparison
- portfolio lab
- future watchlists
- future screeners
- future AI insight modules

## What This Design System Should Not Change

- data loading logic
- API/data contracts
- financial calculations
- scoring rules
- authentication behavior
- environment variables
- database or Supabase logic
- session behavior

This system is only the frontend visual foundation.
