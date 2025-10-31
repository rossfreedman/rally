# Reference Images

Place the reference screenshot here:

- `schedule-web-reference.png` - Pixel-perfect reference screenshot from the web app

## Usage

The PixelOverlay component uses this image for visual verification. To enable:

1. Add `schedule-web-reference.png` to this directory
2. Update `App.tsx`:
   ```tsx
   <PixelOverlay
     referenceImage={require('./docs/reference/schedule-web-reference.png')}
     enabled={true}
   />
   ```
3. Adjust opacity with on-screen controls to verify pixel-perfect match


