# Design System

## Brand direction

Hannibal should feel:
- serious;
- precise;
- calm;
- modern;
- trustworthy;
- professional;
- not overly corporate;
- not like a generic AI dashboard.

## Colors

Use a restrained palette:

```
Ink:       #111827
Slate:     #475569
Surface:   #F8FAFC
Border:    #E2E8F0
Primary:   #1D4ED8
Success:   #15803D
Warning:   #B45309
Danger:    #B91C1C
Evidence:  #0369A1
```

Use color plus text/icon.

## Typography

- Inter or Geist for application UI;
- a readable serif or legal-document font for document preview only;
- clear hierarchy;
- comfortable line height;
- no excessive all-caps.

## Spacing

Use a consistent spacing scale:

```
4, 8, 12, 16, 24, 32, 48, 64
```

## Radius

Use restrained radius:

```
Small controls: 6px
Cards: 10px
Dialogs: 12px
```

Avoid making every element a floating rounded card.

## Shadows

Use subtle shadows only for:
- dialogs;
- popovers;
- elevated workspace panels.

## Animation

Follow Emil Kowalski's principle: animation should enrich the experience, not decorate it. Keep most transitions under 300ms, with larger elements moving more slowly and exit transitions often faster than entrance transitions.

Use motion for:
- step transitions;
- evidence panel opening;
- validation updates;
- toast confirmation;
- section regeneration;
- status changes.

Do not animate:
- every card;
- every table row;
- large document text;
- warnings repeatedly;
- navigation unnecessarily.

## Design-token CSS

```css
:root {
  --color-bg: 248 250 252;
  --color-surface: 255 255 255;
  --color-text: 17 24 39;
  --color-muted: 71 85 105;
  --color-border: 226 232 240;
  --color-primary: 29 78 216;
  --color-success: 21 128 61;
  --color-warning: 180 83 9;
  --color-danger: 185 28 28;

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-6: 24px;
  --space-8: 32px;
  --space-12: 48px;

  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 12px;
}
```

## Component states

Every component should define:
- default;
- hover;
- focus;
- active;
- disabled;
- loading;
- error;
- empty;
- success;
- destructive.

Storybook is useful for documenting and testing these states in isolation.