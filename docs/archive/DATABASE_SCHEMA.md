# Rally Database Schema Documentation

## Overview

The Rally platform tennis management application uses a PostgreSQL database with a relational schema designed to support platform tennis league management, player availability tracking, user authentication, and administrative functions.

## Database Tables

### Core Entity Tables

#### 1. `users` - User Authentication & Profile Management
Stores user account information and authentication data.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `integer` | PRIMARY KEY | Auto-incrementing user identifier |
| `email` | `varchar(255)` | NOT NULL, UNIQUE | User's email address (login identifier) |
| `password_hash` | `varchar(255)` | NOT NULL | Encrypted password using Werkzeug PBKDF2 |
| `first_name` | `varchar(255)` | NOT NULL | User's first name |
| `last_name` | `varchar(255)` | NOT NULL | User's last name |
| `club_id` | `integer` | FOREIGN KEY → `clubs(id)` | Associated tennis club |
| `series_id` | `integer` | FOREIGN KEY → `series(id)` | Associated series/division |
| `league_id` | `integer` | FOREIGN KEY → `leagues(id)` | Associated league organization |
| `tenniscores_player_id` | `varchar(255)` | | External player ID from TennisCores system |
| `club_automation_password` | `varchar(255)` | | Password for club automation features |
| `is_admin` | `boolean` | NOT NULL, DEFAULT false | Administrative privileges flag |
| `created_at` | `timestamp` | DEFAULT CURRENT_TIMESTAMP | Account creation timestamp |
| `last_login` | `timestamp` | | Last successful login timestamp |

**Indexes:**
- `idx_user_email` on `email`
- `idx_users_league_id` on `league_id`
- `idx_users_tenniscores_player_id` on `tenniscores_player_id`

#### 2. `clubs` - Tennis Club Management
Stores information about tennis clubs/facilities.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `integer` | PRIMARY KEY | Auto-incrementing club identifier |
| `name` | `varchar(255)` | NOT NULL, UNIQUE | Club name (e.g., "Barrington Hills CC") |

**Sample Data:**
- Barrington Hills CC
- Biltmore CC
- Birchwood
- Briarwood
- Bryn Mawr

#### 3. `series` - Competition Series/Divisions
Stores information about different competitive divisions within leagues.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `integer` | PRIMARY KEY | Auto-incrementing series identifier |
| `name` | `varchar(255)` | NOT NULL, UNIQUE | Series name (e.g., "Chicago 19") |

**Sample Data:**
- Chicago 11
- Chicago 13
- Chicago 15
- Chicago 17
- Chicago 19

#### 4. `leagues` - League Organizations
Stores information about different platform tennis league organizations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `integer` | PRIMARY KEY | Auto-incrementing league identifier |
| `league_id` | `varchar(255)` | NOT NULL, UNIQUE | League identifier code |
| `league_name` | `varchar(255)` | NOT NULL | Full league name |
| `league_url` | `varchar(512)` | | Official league website URL |
| `created_at` | `timestamp` | DEFAULT CURRENT_TIMESTAMP | League creation timestamp |

**Supported Leagues:**
- **APTA_CHICAGO**: APTA Chicago (https://aptachicago.tenniscores.com/)
- **APTA_NATIONAL**: APTA National (https://apta.tenniscores.com/)
- **NSTF**: North Shore Tennis Foundation (https://nstf.org/)

**Indexes:**
- `idx_leagues_league_id` on `league_id`

### Junction Tables (Many-to-Many Relationships)

#### 5. `club_leagues` - Club-League Associations
Links clubs to the leagues they participate in.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `integer` | PRIMARY KEY | Auto-incrementing identifier |
| `club_id` | `integer` | NOT NULL, FOREIGN KEY → `clubs(id)` | Associated club |
| `league_id` | `integer` | NOT NULL, FOREIGN KEY → `leagues(id)` | Associated league |
| `created_at` | `timestamp` | DEFAULT CURRENT_TIMESTAMP | Association creation timestamp |

**Constraints:**
- UNIQUE constraint on (`club_id`, `league_id`) - prevents duplicate associations
- CASCADE DELETE on both foreign keys

**Indexes:**
- `idx_club_leagues_club_id` on `club_id`
- `idx_club_leagues_league_id` on `league_id`

#### 6. `series_leagues` - Series-League Associations
Links series/divisions to their parent leagues.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `integer` | PRIMARY KEY | Auto-incrementing identifier |
| `series_id` | `integer` | NOT NULL, FOREIGN KEY → `series(id)` | Associated series |
| `league_id` | `integer` | NOT NULL, FOREIGN KEY → `leagues(id)` | Associated league |
| `created_at` | `timestamp` | DEFAULT CURRENT_TIMESTAMP | Association creation timestamp |

**Constraints:**
- UNIQUE constraint on (`series_id`, `league_id`) - prevents duplicate associations
- CASCADE DELETE on both foreign keys

**Indexes:**
- `idx_series_leagues_series_id` on `series_id`
- `idx_series_leagues_league_id` on `league_id`

### Feature Tables

#### 7. `player_availability` - Player Match Availability
Tracks player availability for specific match dates.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `integer` | PRIMARY KEY | Auto-incrementing identifier |
| `player_name` | `varchar(255)` | NOT NULL | Player's full name |
| `match_date` | `timestamp with time zone` | NOT NULL | Match date (must be midnight UTC) |
| `availability_status` | `integer` | NOT NULL, DEFAULT 3 | Availability status (1=Available, 2=Maybe, 3=Unavailable) |
| `series_id` | `integer` | NOT NULL, FOREIGN KEY → `series(id)` | Associated series |
| `tenniscores_player_id` | `varchar(50)` | | External player ID from TennisCores |
| `updated_at` | `timestamp` | DEFAULT CURRENT_TIMESTAMP | Last update timestamp |

**Constraints:**
- UNIQUE constraint on (`player_name`, `match_date`, `series_id`)
- UNIQUE constraint on (`tenniscores_player_id`, `match_date`, `series_id`) when `tenniscores_player_id` is not null
- CHECK constraint: `availability_status` must be 1, 2, or 3
- CHECK constraint: `match_date` must be midnight UTC (ensures consistent date handling)

**Indexes:**
- `idx_player_availability` on (`player_name`, `match_date`, `series_id`)
- `idx_player_availability_date_series` on (`match_date`, `series_id`)
- `idx_player_availability_tenniscores_id` on `tenniscores_player_id`

#### 8. `user_activity_logs` - Activity Tracking
Logs user activities for analytics and security monitoring.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `integer` | PRIMARY KEY | Auto-incrementing identifier |
| `user_email` | `varchar(255)` | NOT NULL | Email of the user performing the action |
| `activity_type` | `varchar(255)` | NOT NULL | Type of activity (auth, page_visit, etc.) |
| `page` | `varchar(255)` | | Page or endpoint accessed |
| `action` | `text` | | Specific action performed |
| `details` | `text` | | Additional details about the activity |
| `ip_address` | `varchar(45)` | | User's IP address (supports IPv6) |
| `timestamp` | `timestamp` | DEFAULT CURRENT_TIMESTAMP | When the activity occurred |

**Indexes:**
- `idx_user_activity_logs_user_email` on (`user_email`, `timestamp`)

#### 9. `user_instructions` - Rally AI Instructions
Stores user-specific instructions for the Rally AI assistant.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `integer` | PRIMARY KEY | Auto-incrementing identifier |
| `user_email` | `varchar(255)` | NOT NULL | Email of the user who created the instruction |
| `instruction` | `text` | NOT NULL | The instruction text for Rally AI |
| `series_id` | `integer` | FOREIGN KEY → `series(id)` | Optional series-specific instruction |
| `team_id` | `integer` | | Optional team-specific instruction |
| `created_at` | `timestamp` | DEFAULT CURRENT_TIMESTAMP | When the instruction was created |
| `is_active` | `boolean` | DEFAULT true | Whether the instruction is currently active |

**Indexes:**
- `idx_user_instructions_email` on `user_email`

## Database Relationships

### Entity Relationship Diagram (ERD)

```
leagues (1) ←→ (M) club_leagues (M) ←→ (1) clubs
   ↑                                        ↑
   │                                        │
   │ (1)                                    │ (1)
   │                                        │
   ↓                                        ↓
series_leagues (M) ←→ (1) series      users (M)
   ↑                       ↑              ↑
   │                       │              │
   │ (M)                   │ (1)          │ (1)
   │                       │              │
   ↓                       ↓              ↓
leagues (1)        player_availability   user_instructions
                          (M)                (M)
                           │
                           │ (M)
                           ↓
                    user_activity_logs
                          (M)
```

### Key Relationships

1. **Users belong to**: One Club, One Series, One League
2. **Clubs can participate in**: Multiple Leagues (many-to-many)
3. **Series can belong to**: Multiple Leagues (many-to-many)
4. **Player Availability is tied to**: One Series per record
5. **User Instructions can be**: Global or Series-specific
6. **Activity Logs track**: All user actions across the platform

## Data Integrity Features

### Foreign Key Constraints
- All foreign keys are properly constrained with appropriate CASCADE rules
- Orphaned records are prevented through referential integrity

### Unique Constraints
- Email addresses are unique across all users
- Club names and series names are unique
- League IDs are unique
- Player availability prevents duplicate entries per player/date/series

### Check Constraints
- Availability status values are restricted to valid options (1, 2, 3)
- Match dates are enforced to be midnight UTC for consistent date handling

### Indexes
- Strategic indexing on frequently queried columns
- Composite indexes for common query patterns
- Foreign key columns are indexed for join performance

## Security Considerations

### Password Security
- Passwords are hashed using Werkzeug's PBKDF2 implementation
- Legacy SHA-256 passwords are supported but converted on next login

### Data Privacy
- User activity is logged for security but respects privacy
- IP addresses are stored for security monitoring
- Sensitive club automation passwords are stored separately

### Access Control
- Admin flag controls administrative access
- Series and club associations control data visibility
- League associations ensure proper data segregation

## Performance Optimizations

### Indexing Strategy
- Primary keys on all tables for efficient lookups
- Foreign key columns indexed for join performance
- Composite indexes on frequently queried column combinations
- Unique constraints double as performance indexes

### Date Handling
- Match dates stored as timestamp with timezone
- UTC midnight constraint ensures consistent date calculations
- Timezone-aware queries for proper date filtering

### Query Optimization
- Junction tables enable efficient many-to-many queries
- Proper normalization reduces data redundancy
- Strategic denormalization (player names) for common queries

## Migration History

The database schema has evolved through several migrations:
- **Baseline Schema**: Core user, club, and series tables
- **Leagues Migration**: Added comprehensive league support
- **Availability Enhancements**: Added TennisCores integration and improved constraints
- **User Instructions**: Added Rally AI instruction storage
- **Performance Improvements**: Added strategic indexes and constraints

## Backup and Recovery

### Railway Environment
- Automated backups through Railway's PostgreSQL service
- Point-in-time recovery capabilities
- High availability with automatic failover

### Local Development
- Regular exports via `pg_dump` for development snapshots
- Schema versioning through migration scripts
- Test data seeding for development environments 