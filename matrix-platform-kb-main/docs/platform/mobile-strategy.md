# Mobile Strategy — PWA, Responsive Design, Offline

> **For Lovable**: This document defines how Matrix Apps work on mobile devices.

---

## Decision: PWA Over Native

| Factor | Rationale |
|--------|-----------|
| Cross-platform | Single codebase for iOS, Android, web |
| No app store | Instant updates, no review delays |
| Shared codebase | Web + mobile from same build |
| Cost | Efficient for small team |

## PWA Capabilities

| Feature | Implementation |
|---------|----------------|
| Add to home screen | Web manifest, service worker |
| Push notifications | Web Push API |
| Offline browsing | Cached listing data + images |

## Offline Requirements

| Capability | Scope |
|------------|-------|
| Property browsing | Cached listing data + images |
| Appointment notes | Sync on reconnect |
| Recently viewed history | Local storage |

## Mobile UX

| Element | Requirement |
|---------|--------------|
| Listing cards | Touch-friendly, swipe navigation |
| Virtual tour | iframe/WebView integration |
| Media | High-res with lazy loading |
| Auth | Biometric (WebAuthn) where supported |

## Responsive Design

- **Framework**: All shadcn/ui components are responsive
- **Breakpoints**: Mobile (<768px), tablet (768–1024px), desktop (>1024px)
- **Sidebar**: Collapses to hamburger on mobile

## Cross-Reference

| For | See |
|-----|-----|
| App build patterns, auth | [app-template.md](app-template.md) |
| App catalog and platform apps | [app-catalog.md](app-catalog.md) |
