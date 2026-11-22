# Assets Directory

This directory contains static, client-bundled application assets.

## Supported Content

- SVG graphics, logos, and vector illustrations
- Raster images (PNG, WebP, JPEG)
- Document templates and static visual resources

## Import Convention

Import assets directly in TypeScript/TSX modules to benefit from Vite asset hashing:

```ts
import logoUrl from '@/assets/logo.svg'
```
