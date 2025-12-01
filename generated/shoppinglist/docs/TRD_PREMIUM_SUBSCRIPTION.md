# Technical Requirements Document (TRD)
## Premium Subscription Tier - Shopping List Application

**Document Version:** 1.0
**Created:** December 1, 2025
**Status:** Draft - Awaiting Review

---

## 1. Overview

### 1.1 Purpose
This document defines the technical requirements, architecture, and implementation specifications for adding premium subscription functionality to the Shopping List application.

### 1.2 Scope
This TRD covers:
- Database schema design and migration
- Payment processing integration (Stripe)
- API endpoint specifications
- Authentication and authorization enhancements
- Frontend implementation requirements
- Real-time collaboration infrastructure
- DevOps and deployment considerations

### 1.3 Current System Summary
| Component | Current State |
|-----------|---------------|
| Backend | Node.js + Express.js |
| Frontend | Vanilla HTML/CSS/JavaScript |
| Authentication | Passport.js + Google OAuth 2.0 |
| Data Storage | In-memory Map (no persistence) |
| Session | express-session (in-memory) |
| Hosting | Local development only |

---

## 2. Architecture Overview

### 2.1 Target Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                               │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │   Web App    │  │  Mobile PWA  │  │   (Future)   │                  │
│  │  (Vanilla)   │  │   (Future)   │  │  Native Apps │                  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                  │
└─────────┼─────────────────┼─────────────────┼───────────────────────────┘
          │                 │                 │
          └────────────────┬┘─────────────────┘
                           │
                    ┌──────▼──────┐
                    │   Nginx     │
                    │  (Reverse   │
                    │   Proxy)    │
                    └──────┬──────┘
                           │
┌──────────────────────────┼──────────────────────────────────────────────┐
│                          │          API LAYER                           │
├──────────────────────────┼──────────────────────────────────────────────┤
│                   ┌──────▼──────┐                                       │
│                   │   Express   │                                       │
│                   │   Server    │                                       │
│                   └──────┬──────┘                                       │
│                          │                                              │
│     ┌────────────────────┼────────────────────┐                        │
│     │                    │                    │                        │
│  ┌──▼──────┐      ┌──────▼──────┐      ┌──────▼──────┐                 │
│  │  Auth   │      │ Shopping    │      │Subscription │                 │
│  │ Routes  │      │ List API    │      │    API      │                 │
│  └─────────┘      └─────────────┘      └──────┬──────┘                 │
│                                               │                        │
│                                        ┌──────▼──────┐                 │
│                                        │   Stripe    │                 │
│                                        │  Webhooks   │                 │
│                                        └─────────────┘                 │
└─────────────────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────────────────┐
│                          │         DATA LAYER                           │
├──────────────────────────┼──────────────────────────────────────────────┤
│     ┌────────────────────┼────────────────────┐                        │
│     │                    │                    │                        │
│  ┌──▼──────┐      ┌──────▼──────┐      ┌──────▼──────┐                 │
│  │PostgreSQL│     │   Redis     │      │    S3      │                 │
│  │(Primary) │     │  (Cache/    │      │ (Backups)  │                 │
│  │          │     │  Sessions)  │      │            │                 │
│  └──────────┘     └─────────────┘      └────────────┘                 │
└─────────────────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────────────────┐
│                          │      EXTERNAL SERVICES                       │
├──────────────────────────┼──────────────────────────────────────────────┤
│  ┌──────────┐     ┌──────▼──────┐      ┌────────────┐                  │
│  │  Google  │     │   Stripe    │      │  SendGrid  │                  │
│  │  OAuth   │     │  Payments   │      │   Email    │                  │
│  └──────────┘     └─────────────┘      └────────────┘                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Technology Stack Additions

| Component | Technology | Justification |
|-----------|------------|---------------|
| Database | PostgreSQL 15+ | ACID compliance, JSON support, proven reliability |
| ORM | Prisma | Type-safe, migrations, excellent DX |
| Cache/Sessions | Redis | Fast session storage, real-time pub/sub |
| Payments | Stripe | Industry standard, excellent documentation |
| Email | SendGrid | Reliable transactional email |
| Real-time | Socket.io | WebSocket abstraction, fallback support |
| File Storage | AWS S3 | Backups, exports |

---

## 3. Database Design

### 3.1 Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│      User       │       │  Subscription   │       │     Family      │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │──────<│ user_id (FK)    │       │ id (PK)         │
│ google_id       │       │ id (PK)         │   ┌──>│ admin_id (FK)   │
│ email           │       │ stripe_customer │   │   │ name            │
│ name            │       │ stripe_sub_id   │   │   │ created_at      │
│ picture         │       │ tier            │   │   └────────┬────────┘
│ created_at      │       │ status          │   │            │
│ updated_at      │       │ period_start    │   │            │
│ family_id (FK)  │───────│ period_end      │   │   ┌────────▼────────┐
│ family_role     │   │   │ trial_end       │   │   │ FamilyInvite    │
└────────┬────────┘   │   │ cancel_at       │   │   ├─────────────────┤
         │            │   └─────────────────┘   │   │ id (PK)         │
         │            │                         │   │ family_id (FK)  │
         │            └─────────────────────────┘   │ email           │
         │                                          │ token           │
         │                                          │ expires_at      │
┌────────▼────────┐       ┌─────────────────┐      │ status          │
│  ShoppingList   │       │   ListShare     │      └─────────────────┘
├─────────────────┤       ├─────────────────┤
│ id (PK)         │──────<│ list_id (FK)    │
│ user_id (FK)    │       │ id (PK)         │
│ family_id (FK)  │       │ share_token     │
│ name            │       │ permission      │
│ icon            │       │ expires_at      │
│ color           │       └─────────────────┘
│ is_template     │
│ folder_id (FK)  │       ┌─────────────────┐
│ position        │       │   ListFolder    │
│ archived_at     │       ├─────────────────┤
│ created_at      │   ┌──>│ id (PK)         │
│ updated_at      │───┘   │ user_id (FK)    │
└────────┬────────┘       │ name            │
         │                │ position        │
         │                └─────────────────┘
┌────────▼────────┐
│  ShoppingItem   │       ┌─────────────────┐
├─────────────────┤       │    Category     │
│ id (PK)         │       ├─────────────────┤
│ list_id (FK)    │   ┌──>│ id (PK)         │
│ text            │───┘   │ user_id (FK)    │
│ completed       │       │ name            │
│ quantity        │       │ color           │
│ unit            │       │ icon            │
│ category_id(FK) │       │ position        │
│ assigned_to(FK) │       │ is_preset       │
│ notes           │       └─────────────────┘
│ price           │
│ recurring_id(FK)│       ┌─────────────────┐
│ position        │       │ RecurringItem   │
│ created_by (FK) │       ├─────────────────┤
│ created_at      │   ┌──>│ id (PK)         │
│ updated_at      │───┘   │ user_id (FK)    │
│ completed_at    │       │ list_id (FK)    │
└─────────────────┘       │ template_item   │
                          │ frequency       │
┌─────────────────┐       │ next_add_date   │
│  ItemHistory    │       │ is_active       │
├─────────────────┤       └─────────────────┘
│ id (PK)         │
│ user_id (FK)    │       ┌─────────────────┐
│ item_text       │       │ ActivityLog     │
│ list_id (FK)    │       ├─────────────────┤
│ category_id     │       │ id (PK)         │
│ purchased_at    │       │ family_id (FK)  │
│ price           │       │ user_id (FK)    │
│ store           │       │ list_id (FK)    │
└─────────────────┘       │ action          │
                          │ item_id (FK)    │
                          │ details (JSON)  │
                          │ created_at      │
                          └─────────────────┘
```

### 3.2 Schema Definition (Prisma)

```prisma
// prisma/schema.prisma

generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

// ============== USER & AUTH ==============

model User {
  id            String    @id @default(cuid())
  googleId      String    @unique @map("google_id")
  email         String    @unique
  name          String
  picture       String?

  // Subscription
  subscription  Subscription?

  // Family
  family        Family?   @relation("FamilyMembers", fields: [familyId], references: [id])
  familyId      String?   @map("family_id")
  familyRole    FamilyRole @default(MEMBER) @map("family_role")
  adminOfFamily Family?   @relation("FamilyAdmin")

  // Shopping Data
  lists         ShoppingList[]
  items         ShoppingItem[] @relation("CreatedBy")
  assignedItems ShoppingItem[] @relation("AssignedTo")
  categories    Category[]
  folders       ListFolder[]
  recurringItems RecurringItem[]
  itemHistory   ItemHistory[]
  activityLogs  ActivityLog[]

  createdAt     DateTime  @default(now()) @map("created_at")
  updatedAt     DateTime  @updatedAt @map("updated_at")

  @@map("users")
}

enum FamilyRole {
  ADMIN
  MEMBER
}

// ============== SUBSCRIPTION ==============

model Subscription {
  id              String   @id @default(cuid())
  user            User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  userId          String   @unique @map("user_id")

  stripeCustomerId    String   @unique @map("stripe_customer_id")
  stripeSubscriptionId String? @unique @map("stripe_subscription_id")
  stripePriceId       String?  @map("stripe_price_id")

  tier            SubscriptionTier @default(FREE)
  status          SubscriptionStatus @default(ACTIVE)

  currentPeriodStart DateTime? @map("current_period_start")
  currentPeriodEnd   DateTime? @map("current_period_end")
  trialEnd          DateTime? @map("trial_end")
  cancelAt          DateTime? @map("cancel_at")
  canceledAt        DateTime? @map("canceled_at")

  createdAt       DateTime @default(now()) @map("created_at")
  updatedAt       DateTime @updatedAt @map("updated_at")

  @@map("subscriptions")
}

enum SubscriptionTier {
  FREE
  PREMIUM
  FAMILY
}

enum SubscriptionStatus {
  ACTIVE
  TRIALING
  PAST_DUE
  CANCELED
  UNPAID
  INCOMPLETE
}

// ============== FAMILY ==============

model Family {
  id          String    @id @default(cuid())
  name        String    @default("My Family")

  admin       User      @relation("FamilyAdmin", fields: [adminId], references: [id])
  adminId     String    @unique @map("admin_id")

  members     User[]    @relation("FamilyMembers")
  invites     FamilyInvite[]
  lists       ShoppingList[]
  activities  ActivityLog[]

  createdAt   DateTime  @default(now()) @map("created_at")
  updatedAt   DateTime  @updatedAt @map("updated_at")

  @@map("families")
}

model FamilyInvite {
  id          String    @id @default(cuid())
  family      Family    @relation(fields: [familyId], references: [id], onDelete: Cascade)
  familyId    String    @map("family_id")

  email       String
  token       String    @unique
  status      InviteStatus @default(PENDING)

  expiresAt   DateTime  @map("expires_at")
  createdAt   DateTime  @default(now()) @map("created_at")

  @@unique([familyId, email])
  @@map("family_invites")
}

enum InviteStatus {
  PENDING
  ACCEPTED
  EXPIRED
  REVOKED
}

// ============== SHOPPING LISTS ==============

model ListFolder {
  id          String    @id @default(cuid())
  user        User      @relation(fields: [userId], references: [id], onDelete: Cascade)
  userId      String    @map("user_id")

  name        String
  position    Int       @default(0)

  lists       ShoppingList[]

  createdAt   DateTime  @default(now()) @map("created_at")

  @@map("list_folders")
}

model ShoppingList {
  id          String    @id @default(cuid())

  user        User      @relation(fields: [userId], references: [id], onDelete: Cascade)
  userId      String    @map("user_id")

  family      Family?   @relation(fields: [familyId], references: [id])
  familyId    String?   @map("family_id")

  folder      ListFolder? @relation(fields: [folderId], references: [id])
  folderId    String?   @map("folder_id")

  name        String    @default("Shopping List")
  icon        String?
  color       String?
  isTemplate  Boolean   @default(false) @map("is_template")
  position    Int       @default(0)

  items       ShoppingItem[]
  shares      ListShare[]
  activities  ActivityLog[]
  recurringItems RecurringItem[]

  archivedAt  DateTime? @map("archived_at")
  createdAt   DateTime  @default(now()) @map("created_at")
  updatedAt   DateTime  @updatedAt @map("updated_at")

  @@map("shopping_lists")
}

model ListShare {
  id          String    @id @default(cuid())
  list        ShoppingList @relation(fields: [listId], references: [id], onDelete: Cascade)
  listId      String    @map("list_id")

  token       String    @unique
  permission  SharePermission @default(VIEW)

  expiresAt   DateTime? @map("expires_at")
  createdAt   DateTime  @default(now()) @map("created_at")

  @@map("list_shares")
}

enum SharePermission {
  VIEW
  EDIT
}

// ============== SHOPPING ITEMS ==============

model ShoppingItem {
  id          String    @id @default(cuid())

  list        ShoppingList @relation(fields: [listId], references: [id], onDelete: Cascade)
  listId      String    @map("list_id")

  text        String
  completed   Boolean   @default(false)
  quantity    Float?
  unit        String?
  notes       String?
  price       Decimal?  @db.Decimal(10, 2)
  position    Int       @default(0)

  category    Category? @relation(fields: [categoryId], references: [id])
  categoryId  String?   @map("category_id")

  assignedTo  User?     @relation("AssignedTo", fields: [assignedToId], references: [id])
  assignedToId String?  @map("assigned_to_id")

  createdBy   User      @relation("CreatedBy", fields: [createdById], references: [id])
  createdById String    @map("created_by_id")

  recurring   RecurringItem? @relation(fields: [recurringId], references: [id])
  recurringId String?   @map("recurring_id")

  completedAt DateTime? @map("completed_at")
  createdAt   DateTime  @default(now()) @map("created_at")
  updatedAt   DateTime  @updatedAt @map("updated_at")

  @@map("shopping_items")
}

// ============== CATEGORIES ==============

model Category {
  id          String    @id @default(cuid())

  user        User?     @relation(fields: [userId], references: [id], onDelete: Cascade)
  userId      String?   @map("user_id")

  name        String
  color       String    @default("#6366f1")
  icon        String?
  position    Int       @default(0)
  isPreset    Boolean   @default(false) @map("is_preset")

  items       ShoppingItem[]

  @@unique([userId, name])
  @@map("categories")
}

// ============== RECURRING ITEMS ==============

model RecurringItem {
  id          String    @id @default(cuid())

  user        User      @relation(fields: [userId], references: [id], onDelete: Cascade)
  userId      String    @map("user_id")

  list        ShoppingList @relation(fields: [listId], references: [id], onDelete: Cascade)
  listId      String    @map("list_id")

  templateItem Json     @map("template_item")
  frequency   RecurrenceFrequency
  customDays  Int[]     @default([]) @map("custom_days")

  nextAddDate DateTime  @map("next_add_date")
  isActive    Boolean   @default(true) @map("is_active")

  items       ShoppingItem[]

  createdAt   DateTime  @default(now()) @map("created_at")
  updatedAt   DateTime  @updatedAt @map("updated_at")

  @@map("recurring_items")
}

enum RecurrenceFrequency {
  DAILY
  WEEKLY
  BIWEEKLY
  MONTHLY
  CUSTOM
}

// ============== HISTORY & ACTIVITY ==============

model ItemHistory {
  id          String    @id @default(cuid())

  user        User      @relation(fields: [userId], references: [id], onDelete: Cascade)
  userId      String    @map("user_id")

  itemText    String    @map("item_text")
  listId      String?   @map("list_id")
  categoryId  String?   @map("category_id")
  price       Decimal?  @db.Decimal(10, 2)
  store       String?

  purchasedAt DateTime  @default(now()) @map("purchased_at")

  @@index([userId, purchasedAt])
  @@map("item_history")
}

model ActivityLog {
  id          String    @id @default(cuid())

  family      Family?   @relation(fields: [familyId], references: [id], onDelete: Cascade)
  familyId    String?   @map("family_id")

  user        User      @relation(fields: [userId], references: [id], onDelete: Cascade)
  userId      String    @map("user_id")

  list        ShoppingList? @relation(fields: [listId], references: [id], onDelete: SetNull)
  listId      String?   @map("list_id")

  action      ActivityAction
  details     Json      @default("{}")

  createdAt   DateTime  @default(now()) @map("created_at")

  @@index([familyId, createdAt])
  @@map("activity_logs")
}

enum ActivityAction {
  ITEM_ADDED
  ITEM_COMPLETED
  ITEM_DELETED
  ITEM_EDITED
  LIST_CREATED
  LIST_ARCHIVED
  MEMBER_JOINED
  MEMBER_LEFT
}
```

### 3.3 Database Migrations Strategy

```
Migration Order:
1. 001_init_users           - Create users table with Google auth fields
2. 002_add_subscriptions    - Add subscription management tables
3. 003_add_shopping_lists   - Migrate from in-memory to persistent lists
4. 004_add_categories       - Add category system with presets
5. 005_add_families         - Add family/collaboration tables
6. 006_add_history          - Add purchase history tracking
7. 007_add_recurring        - Add recurring items system
8. 008_add_activity_logs    - Add activity logging
```

---

## 4. API Specifications

### 4.1 API Design Principles
- RESTful endpoints
- JSON request/response format
- JWT-based authentication for API (alongside session)
- Consistent error response format
- Rate limiting per tier
- API versioning (v1)

### 4.2 Authentication Enhancements

#### Session Enhancement
```typescript
interface SessionData {
  userId: string;
  tier: SubscriptionTier;
  familyId?: string;
  familyRole?: FamilyRole;
}
```

#### Middleware: requireAuth
```typescript
// Validates session and attaches user to request
function requireAuth(req, res, next) {
  if (!req.session.userId) {
    return res.status(401).json({ error: 'Not authenticated' });
  }
  next();
}
```

#### Middleware: requireTier
```typescript
// Validates user has required subscription tier
function requireTier(minTier: SubscriptionTier) {
  return (req, res, next) => {
    const userTier = req.session.tier;
    const tierOrder = { FREE: 0, PREMIUM: 1, FAMILY: 2 };

    if (tierOrder[userTier] < tierOrder[minTier]) {
      return res.status(403).json({
        error: 'Upgrade required',
        requiredTier: minTier,
        currentTier: userTier
      });
    }
    next();
  };
}
```

### 4.3 Subscription API Endpoints

#### POST /api/v1/subscriptions/checkout
Create Stripe Checkout session for subscription.

```typescript
// Request
{
  tier: 'PREMIUM' | 'FAMILY',
  billingPeriod: 'monthly' | 'annual'
}

// Response (200)
{
  checkoutUrl: string,
  sessionId: string
}

// Error (400)
{
  error: 'Already subscribed to this tier'
}
```

#### GET /api/v1/subscriptions/current
Get current subscription status.

```typescript
// Response (200)
{
  tier: 'FREE' | 'PREMIUM' | 'FAMILY',
  status: 'ACTIVE' | 'TRIALING' | 'PAST_DUE' | 'CANCELED',
  currentPeriodEnd: '2025-02-01T00:00:00Z',
  cancelAt: null | '2025-02-01T00:00:00Z',
  trialEnd: null | '2025-01-15T00:00:00Z',
  features: {
    maxLists: number | null,
    maxItemsPerList: number | null,
    canShare: boolean,
    maxFamilyMembers: number,
    hasSmartSuggestions: boolean,
    hasRecurringItems: boolean,
    historyDays: number,
    hasExport: boolean
  }
}
```

#### POST /api/v1/subscriptions/portal
Create Stripe Customer Portal session for billing management.

```typescript
// Response (200)
{
  portalUrl: string
}
```

#### POST /api/v1/subscriptions/cancel
Cancel subscription at period end.

```typescript
// Response (200)
{
  success: true,
  cancelAt: '2025-02-01T00:00:00Z'
}
```

#### POST /api/v1/subscriptions/reactivate
Reactivate canceled subscription.

```typescript
// Response (200)
{
  success: true,
  status: 'ACTIVE'
}
```

### 4.4 Stripe Webhook Endpoint

#### POST /api/v1/webhooks/stripe
Handle Stripe webhook events.

```typescript
// Events to Handle:
- checkout.session.completed      // Subscription created
- customer.subscription.created   // Subscription activated
- customer.subscription.updated   // Status/tier changed
- customer.subscription.deleted   // Subscription ended
- invoice.paid                    // Payment successful
- invoice.payment_failed          // Payment failed
- customer.updated                // Customer details changed
```

### 4.5 Shopping List API Enhancements

#### GET /api/v1/lists
Get all lists for user.

```typescript
// Response (200)
{
  lists: [
    {
      id: string,
      name: string,
      icon: string | null,
      color: string | null,
      itemCount: number,
      completedCount: number,
      isShared: boolean,
      isFamilyList: boolean,
      folderId: string | null,
      updatedAt: string
    }
  ],
  folders: [
    {
      id: string,
      name: string,
      position: number
    }
  ]
}

// Free tier: Returns single list only
// Premium/Family: Returns all lists
```

#### POST /api/v1/lists
Create new list.

```typescript
// Request
{
  name: string,
  icon?: string,
  color?: string,
  folderId?: string,
  isFamilyList?: boolean  // Family tier only
}

// Response (201)
{
  id: string,
  name: string,
  // ... full list object
}

// Error (403) - Free tier limit
{
  error: 'List limit reached',
  limit: 1,
  requiredTier: 'PREMIUM'
}
```

#### POST /api/v1/lists/:listId/share
Generate share link for list.

```typescript
// Request
{
  permission: 'VIEW',  // Premium: VIEW only, Family: VIEW | EDIT
  expiresIn?: number   // Hours, default 168 (1 week)
}

// Response (200)
{
  shareUrl: string,
  token: string,
  expiresAt: string
}

// Error (403)
{
  error: 'Sharing requires Premium',
  requiredTier: 'PREMIUM'
}
```

### 4.6 Family API Endpoints

#### GET /api/v1/family
Get family details (Family tier only).

```typescript
// Response (200)
{
  id: string,
  name: string,
  members: [
    {
      id: string,
      name: string,
      email: string,
      picture: string | null,
      role: 'ADMIN' | 'MEMBER',
      joinedAt: string
    }
  ],
  pendingInvites: [
    {
      id: string,
      email: string,
      expiresAt: string
    }
  ]
}
```

#### POST /api/v1/family/invite
Invite member to family.

```typescript
// Request
{
  email: string
}

// Response (200)
{
  inviteId: string,
  expiresAt: string
}

// Error (400)
{
  error: 'Member limit reached',
  limit: 6
}
```

#### POST /api/v1/family/invite/:token/accept
Accept family invitation.

```typescript
// Response (200)
{
  success: true,
  family: { ... }
}
```

#### DELETE /api/v1/family/members/:memberId
Remove member from family (admin only).

```typescript
// Response (200)
{
  success: true
}
```

### 4.7 Category API Endpoints

#### GET /api/v1/categories
Get user's categories.

```typescript
// Response (200)
{
  categories: [
    {
      id: string,
      name: string,
      color: string,
      icon: string | null,
      isPreset: boolean,
      itemCount: number
    }
  ]
}
```

#### POST /api/v1/categories
Create custom category (Premium+).

```typescript
// Request
{
  name: string,
  color: string,
  icon?: string
}

// Response (201)
{
  id: string,
  name: string,
  color: string,
  icon: string | null,
  isPreset: false
}

// Error (403) - Free tier
{
  error: 'Custom categories require Premium',
  requiredTier: 'PREMIUM'
}
```

### 4.8 Rate Limiting

| Endpoint Group | Free | Premium | Family |
|----------------|------|---------|--------|
| General API | 100/hour | 1000/hour | 1000/hour |
| List operations | 50/hour | 500/hour | 500/hour |
| Share generation | 5/day | 50/day | 100/day |
| Export | N/A | 10/day | 20/day |

---

## 5. Stripe Integration

### 5.1 Product Configuration

```typescript
// Stripe Products & Prices (to create in Stripe Dashboard)

// Premium Monthly
{
  product: 'prod_premium',
  name: 'Shopping List Premium',
  price: {
    id: 'price_premium_monthly',
    amount: 499,  // $4.99
    currency: 'usd',
    interval: 'month'
  }
}

// Premium Annual
{
  product: 'prod_premium',
  price: {
    id: 'price_premium_annual',
    amount: 4999,  // $49.99
    currency: 'usd',
    interval: 'year'
  }
}

// Family Monthly
{
  product: 'prod_family',
  name: 'Shopping List Family',
  price: {
    id: 'price_family_monthly',
    amount: 999,  // $9.99
    currency: 'usd',
    interval: 'month'
  }
}

// Family Annual
{
  product: 'prod_family',
  price: {
    id: 'price_family_annual',
    amount: 9999,  // $99.99
    currency: 'usd',
    interval: 'year'
  }
}
```

### 5.2 Checkout Session Creation

```typescript
// services/stripe.ts

import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);

interface CreateCheckoutParams {
  userId: string;
  email: string;
  priceId: string;
  successUrl: string;
  cancelUrl: string;
}

async function createCheckoutSession(params: CreateCheckoutParams) {
  const { userId, email, priceId, successUrl, cancelUrl } = params;

  // Get or create Stripe customer
  let customerId = await getStripeCustomerId(userId);

  if (!customerId) {
    const customer = await stripe.customers.create({
      email,
      metadata: { userId }
    });
    customerId = customer.id;
    await saveStripeCustomerId(userId, customerId);
  }

  // Create checkout session
  const session = await stripe.checkout.sessions.create({
    customer: customerId,
    mode: 'subscription',
    payment_method_types: ['card'],
    line_items: [{ price: priceId, quantity: 1 }],
    subscription_data: {
      trial_period_days: 14,
      metadata: { userId }
    },
    success_url: `${successUrl}?session_id={CHECKOUT_SESSION_ID}`,
    cancel_url: cancelUrl,
    allow_promotion_codes: true
  });

  return session;
}
```

### 5.3 Webhook Handler

```typescript
// routes/webhooks.ts

import { buffer } from 'micro';

async function handleStripeWebhook(req, res) {
  const sig = req.headers['stripe-signature'];
  const rawBody = await buffer(req);

  let event;
  try {
    event = stripe.webhooks.constructEvent(
      rawBody,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET
    );
  } catch (err) {
    console.error('Webhook signature verification failed');
    return res.status(400).send(`Webhook Error: ${err.message}`);
  }

  switch (event.type) {
    case 'checkout.session.completed':
      await handleCheckoutComplete(event.data.object);
      break;

    case 'customer.subscription.updated':
      await handleSubscriptionUpdate(event.data.object);
      break;

    case 'customer.subscription.deleted':
      await handleSubscriptionDeleted(event.data.object);
      break;

    case 'invoice.payment_failed':
      await handlePaymentFailed(event.data.object);
      break;
  }

  res.json({ received: true });
}

async function handleCheckoutComplete(session) {
  const subscription = await stripe.subscriptions.retrieve(
    session.subscription
  );

  const userId = subscription.metadata.userId;
  const priceId = subscription.items.data[0].price.id;
  const tier = getTierFromPriceId(priceId);

  await prisma.subscription.upsert({
    where: { userId },
    create: {
      userId,
      stripeCustomerId: session.customer,
      stripeSubscriptionId: subscription.id,
      stripePriceId: priceId,
      tier,
      status: subscription.status === 'trialing' ? 'TRIALING' : 'ACTIVE',
      currentPeriodStart: new Date(subscription.current_period_start * 1000),
      currentPeriodEnd: new Date(subscription.current_period_end * 1000),
      trialEnd: subscription.trial_end
        ? new Date(subscription.trial_end * 1000)
        : null
    },
    update: {
      stripeSubscriptionId: subscription.id,
      stripePriceId: priceId,
      tier,
      status: subscription.status === 'trialing' ? 'TRIALING' : 'ACTIVE',
      currentPeriodStart: new Date(subscription.current_period_start * 1000),
      currentPeriodEnd: new Date(subscription.current_period_end * 1000),
      trialEnd: subscription.trial_end
        ? new Date(subscription.trial_end * 1000)
        : null
    }
  });
}
```

### 5.4 Customer Portal

```typescript
async function createPortalSession(customerId: string, returnUrl: string) {
  const session = await stripe.billingPortal.sessions.create({
    customer: customerId,
    return_url: returnUrl
  });

  return session.url;
}
```

---

## 6. Real-time Collaboration (Family Tier)

### 6.1 Socket.io Integration

```typescript
// services/realtime.ts

import { Server } from 'socket.io';
import { createAdapter } from '@socket.io/redis-adapter';

export function initializeRealtime(httpServer, redisClient) {
  const io = new Server(httpServer, {
    cors: {
      origin: process.env.FRONTEND_URL,
      credentials: true
    }
  });

  // Redis adapter for horizontal scaling
  const pubClient = redisClient.duplicate();
  const subClient = redisClient.duplicate();
  io.adapter(createAdapter(pubClient, subClient));

  // Authentication middleware
  io.use(async (socket, next) => {
    const sessionId = socket.handshake.auth.sessionId;
    const session = await getSession(sessionId);

    if (!session || session.tier !== 'FAMILY') {
      return next(new Error('Unauthorized'));
    }

    socket.userId = session.userId;
    socket.familyId = session.familyId;
    next();
  });

  io.on('connection', (socket) => {
    // Join family room
    if (socket.familyId) {
      socket.join(`family:${socket.familyId}`);
    }

    // Join specific list room
    socket.on('join-list', async (listId) => {
      const hasAccess = await checkListAccess(socket.userId, listId);
      if (hasAccess) {
        socket.join(`list:${listId}`);
      }
    });

    // Leave list room
    socket.on('leave-list', (listId) => {
      socket.leave(`list:${listId}`);
    });

    // Item added
    socket.on('item-added', async (data) => {
      const { listId, item } = data;
      // Broadcast to list room (except sender)
      socket.to(`list:${listId}`).emit('item-added', {
        item,
        addedBy: socket.userId
      });
    });

    // Item updated
    socket.on('item-updated', async (data) => {
      const { listId, itemId, changes } = data;
      socket.to(`list:${listId}`).emit('item-updated', {
        itemId,
        changes,
        updatedBy: socket.userId
      });
    });

    // Item deleted
    socket.on('item-deleted', async (data) => {
      const { listId, itemId } = data;
      socket.to(`list:${listId}`).emit('item-deleted', {
        itemId,
        deletedBy: socket.userId
      });
    });

    // Typing indicator
    socket.on('typing', (data) => {
      const { listId } = data;
      socket.to(`list:${listId}`).emit('user-typing', {
        userId: socket.userId
      });
    });
  });

  return io;
}
```

### 6.2 Client-side Integration

```javascript
// frontend/js/realtime.js

class RealtimeService {
  constructor() {
    this.socket = null;
    this.currentListId = null;
  }

  connect(sessionId) {
    this.socket = io({
      auth: { sessionId }
    });

    this.socket.on('connect', () => {
      console.log('Connected to realtime service');
      if (this.currentListId) {
        this.joinList(this.currentListId);
      }
    });

    this.socket.on('item-added', (data) => {
      this.onItemAdded(data);
    });

    this.socket.on('item-updated', (data) => {
      this.onItemUpdated(data);
    });

    this.socket.on('item-deleted', (data) => {
      this.onItemDeleted(data);
    });

    this.socket.on('user-typing', (data) => {
      this.showTypingIndicator(data.userId);
    });
  }

  joinList(listId) {
    if (this.currentListId) {
      this.socket.emit('leave-list', this.currentListId);
    }
    this.currentListId = listId;
    this.socket.emit('join-list', listId);
  }

  emitItemAdded(listId, item) {
    this.socket.emit('item-added', { listId, item });
  }

  emitItemUpdated(listId, itemId, changes) {
    this.socket.emit('item-updated', { listId, itemId, changes });
  }

  emitItemDeleted(listId, itemId) {
    this.socket.emit('item-deleted', { listId, itemId });
  }
}
```

---

## 7. Email Service Integration

### 7.1 SendGrid Configuration

```typescript
// services/email.ts

import sgMail from '@sendgrid/mail';

sgMail.setApiKey(process.env.SENDGRID_API_KEY);

interface EmailTemplate {
  templateId: string;
  subject: string;
}

const templates: Record<string, EmailTemplate> = {
  WELCOME_PREMIUM: {
    templateId: 'd-xxxxx',
    subject: 'Welcome to Shopping List Premium!'
  },
  TRIAL_STARTED: {
    templateId: 'd-xxxxx',
    subject: 'Your 14-day Premium trial has started'
  },
  TRIAL_ENDING: {
    templateId: 'd-xxxxx',
    subject: 'Your trial ends in 3 days'
  },
  PAYMENT_RECEIVED: {
    templateId: 'd-xxxxx',
    subject: 'Payment confirmation'
  },
  PAYMENT_FAILED: {
    templateId: 'd-xxxxx',
    subject: 'Payment failed - action required'
  },
  SUBSCRIPTION_CANCELED: {
    templateId: 'd-xxxxx',
    subject: 'We\'re sorry to see you go'
  },
  FAMILY_INVITE: {
    templateId: 'd-xxxxx',
    subject: 'You\'ve been invited to join a family'
  }
};

async function sendEmail(
  to: string,
  templateKey: string,
  dynamicData: Record<string, any>
) {
  const template = templates[templateKey];

  await sgMail.send({
    to,
    from: {
      email: 'noreply@shoppinglist.app',
      name: 'Shopping List'
    },
    templateId: template.templateId,
    dynamicTemplateData: dynamicData
  });
}

// Example usage
await sendEmail('user@example.com', 'WELCOME_PREMIUM', {
  name: 'John',
  trialEndDate: 'January 15, 2025'
});
```

---

## 8. Frontend Implementation

### 8.1 New Pages/Components

```
frontend/
├── pages/
│   ├── pricing.html           # Subscription tiers comparison
│   ├── checkout-success.html  # Post-checkout confirmation
│   └── billing.html           # Billing management
├── components/
│   ├── subscription-status.js # Current plan indicator
│   ├── upgrade-modal.js       # Upgrade prompt modal
│   ├── tier-badge.js          # PRO/FAMILY badge
│   ├── family-manager.js      # Family member management
│   └── activity-feed.js       # Family activity stream
└── js/
    ├── subscription.js        # Subscription API calls
    ├── realtime.js            # Socket.io client
    └── feature-flags.js       # Tier-based feature toggles
```

### 8.2 Feature Flag System

```javascript
// js/feature-flags.js

const TIER_FEATURES = {
  FREE: {
    maxLists: 1,
    maxItemsPerList: 25,
    canShare: false,
    maxCategories: 3,
    customCategories: false,
    historyDays: 7,
    smartSuggestions: false,
    recurringItems: false,
    export: false,
    familyMembers: 0,
    realtime: false
  },
  PREMIUM: {
    maxLists: null, // unlimited
    maxItemsPerList: null,
    canShare: true,
    sharePermissions: ['VIEW'],
    maxCategories: null,
    customCategories: true,
    historyDays: 365,
    smartSuggestions: true,
    recurringItems: true,
    export: true,
    familyMembers: 0,
    realtime: false
  },
  FAMILY: {
    maxLists: null,
    maxItemsPerList: null,
    canShare: true,
    sharePermissions: ['VIEW', 'EDIT'],
    maxCategories: null,
    customCategories: true,
    historyDays: 365,
    smartSuggestions: true,
    recurringItems: true,
    export: true,
    familyMembers: 6,
    realtime: true
  }
};

class FeatureFlags {
  constructor(tier) {
    this.tier = tier;
    this.features = TIER_FEATURES[tier];
  }

  canCreateList(currentCount) {
    if (this.features.maxLists === null) return true;
    return currentCount < this.features.maxLists;
  }

  canAddItem(currentCount) {
    if (this.features.maxItemsPerList === null) return true;
    return currentCount < this.features.maxItemsPerList;
  }

  canShare() {
    return this.features.canShare;
  }

  canCreateCategory(currentCount, isCustom) {
    if (!isCustom) return true; // Presets always allowed
    if (!this.features.customCategories) return false;
    if (this.features.maxCategories === null) return true;
    return currentCount < this.features.maxCategories;
  }

  hasFeature(featureName) {
    return !!this.features[featureName];
  }

  getLimit(limitName) {
    return this.features[limitName];
  }
}
```

### 8.3 Upgrade Modal Component

```javascript
// components/upgrade-modal.js

class UpgradeModal {
  constructor() {
    this.element = null;
  }

  show(options = {}) {
    const {
      feature = 'premium features',
      requiredTier = 'PREMIUM',
      trigger = 'generic'
    } = options;

    this.element = document.createElement('div');
    this.element.className = 'upgrade-modal-overlay';
    this.element.innerHTML = `
      <div class="upgrade-modal">
        <button class="close-btn" aria-label="Close">&times;</button>
        <div class="modal-icon">
          <svg><!-- Premium icon --></svg>
        </div>
        <h2>Unlock ${feature}</h2>
        <p>Upgrade to ${requiredTier} to access this feature and more.</p>

        <div class="tier-comparison">
          <div class="tier current">
            <h3>Free</h3>
            <ul>
              <li>1 shopping list</li>
              <li>25 items per list</li>
              <li>3 preset categories</li>
            </ul>
          </div>
          <div class="tier highlight">
            <h3>Premium</h3>
            <p class="price">$4.99/month</p>
            <ul>
              <li>Unlimited lists</li>
              <li>Unlimited items</li>
              <li>Custom categories</li>
              <li>Smart suggestions</li>
              <li>And more...</li>
            </ul>
          </div>
        </div>

        <button class="upgrade-btn">Start 14-Day Free Trial</button>
        <p class="disclaimer">No charge until trial ends. Cancel anytime.</p>
      </div>
    `;

    document.body.appendChild(this.element);

    // Event listeners
    this.element.querySelector('.close-btn').onclick = () => this.hide();
    this.element.querySelector('.upgrade-btn').onclick = () => this.startCheckout();
    this.element.onclick = (e) => {
      if (e.target === this.element) this.hide();
    };

    // Track impression
    analytics.track('upgrade_modal_shown', { feature, trigger });
  }

  hide() {
    this.element?.remove();
  }

  async startCheckout() {
    const response = await fetch('/api/v1/subscriptions/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        tier: 'PREMIUM',
        billingPeriod: 'monthly'
      })
    });

    const { checkoutUrl } = await response.json();
    window.location.href = checkoutUrl;
  }
}
```

---

## 9. Security Considerations

### 9.1 Authentication & Authorization
- Validate session on every API request
- Check tier permissions before feature access
- Validate Stripe webhook signatures
- Use HTTPS in production
- Implement CSRF protection

### 9.2 Data Protection
- Encrypt sensitive data at rest (PII, payment tokens)
- Use parameterized queries (Prisma handles this)
- Validate and sanitize all user inputs
- Implement request rate limiting
- Log security events for audit

### 9.3 Payment Security
- Never store raw card numbers (Stripe handles PCI compliance)
- Verify webhook authenticity
- Use idempotency keys for payment operations
- Implement dunning for failed payments
- Secure refund processing

### 9.4 Family Security
- Verify family membership before data access
- Rate limit invite generation
- Expire invites after 7 days
- Allow only admin to remove members
- Audit log all member changes

---

## 10. Testing Requirements

### 10.1 Unit Tests
```typescript
// tests/unit/subscription.test.ts

describe('SubscriptionService', () => {
  describe('checkTierAccess', () => {
    it('should allow FREE tier to access basic features', () => {});
    it('should block FREE tier from premium features', () => {});
    it('should allow PREMIUM tier to access all non-family features', () => {});
    it('should allow FAMILY tier to access all features', () => {});
  });

  describe('enforceListLimit', () => {
    it('should allow FREE user to create first list', () => {});
    it('should block FREE user from creating second list', () => {});
    it('should allow PREMIUM user to create unlimited lists', () => {});
  });
});
```

### 10.2 Integration Tests
```typescript
// tests/integration/stripe-webhook.test.ts

describe('Stripe Webhooks', () => {
  it('should activate subscription on checkout.session.completed', () => {});
  it('should update tier on subscription upgrade', () => {});
  it('should handle subscription cancellation', () => {});
  it('should mark subscription past_due on payment failure', () => {});
  it('should reject invalid webhook signatures', () => {});
});
```

### 10.3 E2E Tests
```typescript
// tests/e2e/subscription-flow.test.ts

describe('Subscription Flow', () => {
  it('should complete checkout and show premium features', () => {});
  it('should show upgrade modal when hitting free tier limit', () => {});
  it('should allow cancellation through billing portal', () => {});
  it('should retain access until subscription period ends', () => {});
});
```

### 10.4 Stripe Test Mode
- Use Stripe test API keys
- Test card numbers (4242424242424242, etc.)
- Webhook testing with Stripe CLI
- Test clock for subscription lifecycle

---

## 11. Monitoring & Observability

### 11.1 Metrics to Track
| Metric | Tool | Alert Threshold |
|--------|------|-----------------|
| API response time | DataDog/NewRelic | > 500ms |
| Error rate | Sentry | > 1% |
| Stripe webhook failures | Custom | Any failure |
| Database query time | Prisma metrics | > 100ms |
| WebSocket connections | Socket.io metrics | > 10k concurrent |

### 11.2 Business Metrics
- Daily/Monthly Active Users (DAU/MAU)
- Conversion rate (Free → Paid)
- Churn rate
- MRR/ARR
- Trial-to-Paid conversion
- Feature adoption by tier

### 11.3 Logging Strategy
```typescript
// Structured logging format
{
  timestamp: '2025-01-01T12:00:00Z',
  level: 'info',
  service: 'subscription',
  event: 'checkout_completed',
  userId: 'usr_xxx',
  tier: 'PREMIUM',
  billingPeriod: 'monthly',
  amount: 499,
  currency: 'usd'
}
```

---

## 12. Deployment & DevOps

### 12.1 Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# Redis
REDIS_URL=redis://localhost:6379

# Stripe
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRICE_PREMIUM_MONTHLY=price_xxx
STRIPE_PRICE_PREMIUM_ANNUAL=price_xxx
STRIPE_PRICE_FAMILY_MONTHLY=price_xxx
STRIPE_PRICE_FAMILY_ANNUAL=price_xxx

# SendGrid
SENDGRID_API_KEY=SG.xxx

# Auth
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxx
SESSION_SECRET=xxx

# App
FRONTEND_URL=https://app.shoppinglist.com
API_URL=https://api.shoppinglist.com
```

### 12.2 Infrastructure Requirements

| Component | Development | Production |
|-----------|-------------|------------|
| App Server | 1x local | 2x t3.medium (auto-scale) |
| Database | PostgreSQL 15 local | RDS PostgreSQL 15, db.t3.medium |
| Redis | Local Redis | ElastiCache t3.micro |
| Storage | Local filesystem | S3 bucket |
| CDN | None | CloudFront |

### 12.3 CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml

name: Deploy
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: npm ci
      - run: npm test

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to production
        run: |
          # Build and deploy steps
```

---

## 13. Migration Strategy

### 13.1 Data Migration Plan

```
Phase 1: Database Setup
├── Provision PostgreSQL instance
├── Run Prisma migrations
├── Create preset categories
└── Verify connectivity

Phase 2: User Migration
├── Export existing users from OAuth sessions
├── Create user records in PostgreSQL
├── Map Google IDs to new user IDs
└── Default all users to FREE tier

Phase 3: Shopping Data Migration
├── Export in-memory shopping lists
├── Create ShoppingList records
├── Migrate items with proper relationships
└── Verify data integrity

Phase 4: Cutover
├── Enable PostgreSQL as primary store
├── Disable in-memory storage
├── Monitor for issues
└── Rollback plan if needed
```

### 13.2 Rollback Plan
- Keep in-memory storage code (feature flagged)
- Database snapshots before migration
- Quick toggle to revert to in-memory
- Communication plan for users

---

## 14. Implementation Phases

### Phase 1: Foundation (2-3 weeks)
- [ ] PostgreSQL setup and Prisma configuration
- [ ] User table migration
- [ ] Session migration to Redis
- [ ] Basic subscription model
- [ ] Stripe integration (checkout, webhooks)
- [ ] Subscription status API

### Phase 2: Core Premium (2-3 weeks)
- [ ] Multiple lists support
- [ ] Unlimited items
- [ ] Feature flag system
- [ ] Upgrade prompts/modals
- [ ] Billing management page
- [ ] Email notifications (SendGrid)

### Phase 3: Premium Features (3-4 weeks)
- [ ] Custom categories system
- [ ] Tags implementation
- [ ] Smart suggestions engine
- [ ] Recurring items
- [ ] Purchase history extension
- [ ] Export/Import functionality

### Phase 4: Family Tier (3-4 weeks)
- [ ] Family model and invitations
- [ ] Real-time collaboration (Socket.io)
- [ ] Item assignment
- [ ] Activity feed
- [ ] Family management UI

### Phase 5: Polish (1-2 weeks)
- [ ] Performance optimization
- [ ] Analytics integration
- [ ] A/B testing setup
- [ ] Documentation
- [ ] Launch preparation

---

## 15. Open Questions

| Question | Options | Decision | Owner |
|----------|---------|----------|-------|
| Database hosting | RDS vs Supabase vs PlanetScale | TBD | Tech Lead |
| Email provider | SendGrid vs SES vs Postmark | TBD | Tech Lead |
| Hosting platform | AWS vs Vercel vs Railway | TBD | Tech Lead |
| Mobile strategy | PWA first vs native apps | TBD | Product |
| Pricing finalization | $4.99/$9.99 vs other | TBD | Business |

---

## 16. Appendices

### Appendix A: API Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| AUTH_REQUIRED | 401 | Not authenticated |
| TIER_REQUIRED | 403 | Subscription tier insufficient |
| LIMIT_REACHED | 403 | Tier limit exceeded |
| NOT_FOUND | 404 | Resource not found |
| VALIDATION_ERROR | 400 | Invalid request data |
| PAYMENT_FAILED | 402 | Payment processing failed |
| STRIPE_ERROR | 500 | Stripe API error |

### Appendix B: Stripe Test Cards

| Card Number | Scenario |
|-------------|----------|
| 4242424242424242 | Successful payment |
| 4000000000000341 | Card declined |
| 4000000000009995 | Insufficient funds |
| 4000000000000002 | Generic decline |
| 4000002500003155 | 3D Secure required |

### Appendix C: Environment Setup

```bash
# Local development setup
git clone <repo>
cd shopping-list
npm install

# Database setup
docker-compose up -d postgres redis
npx prisma migrate dev
npx prisma db seed

# Start development server
npm run dev

# Stripe webhook forwarding
stripe listen --forward-to localhost:3000/api/v1/webhooks/stripe
```

---

*End of Document*
