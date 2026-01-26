# TODO - Electric Project Tasks

This document tracks planned features and improvements for the Electric project.

---

## Critical Priority

### 1. Enforce Authentication on Resource Endpoints

**Description:**
All resource endpoints (properties, meters, readings) are currently publicly accessible. The authentication system exists but isn't applied to protect resources. Any user can access or modify any property, which is a major security concern.

**Recommended Steps:**
1. Create a `get_current_user` dependency in `app/api/dependencies.py` that extracts and validates JWT from Authorization header
2. Add the dependency to all routes in `properties.py`, `meters.py`, and `readings.py`
3. Modify service functions to filter resources by user ownership (via `user_property` association table)
4. Add 403 Forbidden responses for unauthorized access attempts
5. Update tests to include authentication headers
6. Document the authentication requirements in API docs

**Effort:** Medium (2-3 days)
**Impact:** High - Fixes critical security vulnerability, enables multi-tenant usage

---

### 2. Add Value Validation on Meter Readings

**Description:**
The `MeterReadingBase` schema accepts any Decimal value for meter readings, including negative numbers. Invalid data can corrupt the ledger and produce nonsensical "unmetered" calculations.

**Recommended Steps:**
1. Update `app/schemas/meter_reading.py` to add Field constraints:
   ```python
   value: Decimal = Field(ge=0, le=999999999.999)
   ```
2. Add similar validation to `MeterReadingBulkCreate.main_meter_value` and `submeter_readings` values
3. Add unit tests for validation edge cases (negative, zero, max boundary)
4. Consider adding a warning/flag when readings decrease (possible meter replacement)

**Effort:** Low (2-4 hours)
**Impact:** High - Prevents data corruption, ensures ledger integrity

---

### 3. Core Fly.io Deployment Setup

**Description:**
Set up the foundational deployment infrastructure for Fly.io, enabling the Electric API to run in production with a cost-optimized configuration targeting $2-5/month.

**Recommended Steps:**
1. Create multi-stage `Dockerfile` using `uv` package manager and `python:3.11-slim` base
2. Create `.dockerignore` to exclude unnecessary files from the Docker image
3. Create `fly.toml` with auto-stop, health checks, and cost-optimized VM settings
4. Modify `app/core/config.py` to auto-detect Fly Volumes path for SQLite database
5. Test local Docker build: `docker build -t electric .`
6. Run Fly.io initial setup: `fly launch --no-deploy`
7. Create Fly Volume: `fly volumes create electric_data --region iad --size 1`
8. Set production secrets: `fly secrets set SECRET_KEY="$(openssl rand -hex 32)"`
9. Deploy and verify: `fly deploy && fly status`

**Effort:** Low (2-3 hours)
**Impact:** High - Enables production deployment with minimal cost. Blocking for all other deployment-related tasks.

**Reference:** See `docs/FLYIO_INTEGRATION_PLAN.md` for detailed implementation specifications.

---

## High Priority

### 4. Add Pagination Metadata to List Endpoints

**Description:**
`GET /api/properties/` returns a plain list with no total count. Frontend applications cannot display "Page 1 of 10" or determine when to stop paginating.

**Recommended Steps:**
1. Create a generic `PaginatedResponse[T]` schema in `app/schemas/common.py`:
   ```python
   class PaginatedResponse(BaseModel, Generic[T]):
       items: list[T]
       total: int
       limit: int
       offset: int
   ```
2. Update `property_service.get_properties()` to return count alongside results
3. Update `GET /api/properties/` to return `PaginatedResponse[PropertyResponse]`
4. Apply same pattern to any other list endpoints
5. Update tests to verify pagination metadata

**Effort:** Low (3-4 hours)
**Impact:** High - Essential for any frontend pagination UI

---

### 5. Add Search and Filter Capabilities

**Description:**
Users cannot search properties by name or filter meters by type/kind. As data grows, finding specific resources becomes increasingly difficult.

**Recommended Steps:**
1. Add query parameters to `GET /api/properties/`:
   - `search`: Filter by display_name (case-insensitive contains)
   - `is_active`: Filter by active status
2. Add query parameters to `GET /api/properties/{id}/meters`:
   - `meter_type`: Filter by MAIN_METER or SUB_METER
   - `sub_meter_kind`: Filter by PHYSICAL or VIRTUAL
   - `is_active`: Filter by active status
3. Update service layer to apply filters via SQLAlchemy
4. Add index on `Property.display_name` if not present
5. Document filter parameters in OpenAPI schema

**Effort:** Medium (1 day)
**Impact:** High - Critical for usability as data scales

---

### 6. Add User Profile Management Endpoints

**Description:**
Users can register but cannot view or update their profile, change their password, or set preferences. The `User` model has `default_property_id` and `default_meter_id` fields that are inaccessible.

**Recommended Steps:**
1. Create `app/api/routes/users.py` with:
   - `GET /api/users/me` - Get current user profile
   - `PATCH /api/users/me` - Update profile (phone, defaults)
   - `GET /api/users/me/properties` - List user's associated properties
2. Add `POST /api/auth/change-password` to auth routes:
   - Require current password verification
   - Validate new password strength
3. Create corresponding schemas (`UserUpdate`, `PasswordChange`)
4. Register new router in `main.py`
5. Add comprehensive tests

**Effort:** Medium (1-2 days)
**Impact:** High - Basic user management functionality expected in any app

---

### 7. Add Date Range Queries for Readings

**Description:**
Current API only supports getting readings at an exact timestamp or the latest readings. Users cannot query readings within a date range, which is essential for reporting and analysis.

**Recommended Steps:**
1. Add new endpoint `GET /api/readings/meter/{meter_id}/range`:
   - Query params: `start_date`, `end_date` (required)
   - Optional: `limit`, `offset` for pagination
2. Add service method `get_readings_in_range()`
3. Consider adding `GET /api/readings/property/{property_id}/range` for all meters
4. Add index on `MeterReading.reading_timestamp` if not present
5. Validate that `start_date < end_date`
6. Add tests for edge cases (empty range, large range)

**Effort:** Medium (1 day)
**Impact:** High - Essential for reporting, charts, and data analysis

---

### 8. Automated Deployment Pipeline (CI/CD)

**Description:**
Set up GitHub Actions workflow to automatically test and deploy the application to Fly.io when changes are pushed to the main branch.

**Recommended Steps:**
1. Create `.github/workflows/deploy.yml` with test and deploy jobs
2. Generate Fly.io deploy token: `fly tokens create deploy`
3. Add `FLY_API_TOKEN` secret to GitHub repository settings
4. Test pipeline by pushing a commit to main branch
5. Verify deployment completes successfully

**Effort:** Low (1-2 hours)
**Impact:** Medium-High - Enables continuous deployment, reduces manual deployment overhead, ensures all deployments pass tests.

**Dependencies:** Core Fly.io Deployment must be completed first.

---

## Medium Priority

### 9. Add Soft Delete Endpoints

**Description:**
Models have `is_active` fields but there's no API to deactivate entities. Users must either leave orphaned data or request database-level deletion.

**Recommended Steps:**
1. Add `DELETE /api/properties/{id}` that sets `is_active=False`
2. Add `DELETE /api/meters/{id}` with same behavior
3. Optionally add `POST /api/properties/{id}/restore` to reactivate
4. Update list endpoints to exclude inactive by default (add `include_inactive=false` param)
5. Prevent deletion of properties with active meters (or cascade deactivation)
6. Add tests for delete and restore flows

**Effort:** Low (4-6 hours)
**Impact:** Medium - Improves data lifecycle management

---

### 10. Normalize Empty Result Responses

**Description:**
`get_property_reading_summary` returns `None` for properties with no readings, which requires special handling by clients. Inconsistent empty states complicate frontend development.

**Recommended Steps:**
1. Update `get_property_reading_summary()` to return a consistent structure when no readings exist:
   ```python
   PropertyReadingSummary(
       property_id=property_id,
       reading_timestamp=None,
       main_meter=None,
       submeters=[],
       unmetered=None
   )
   ```
2. Review other endpoints for similar inconsistencies
3. Document expected response shapes in OpenAPI descriptions
4. Update tests to verify empty state responses

**Effort:** Low (2-3 hours)
**Impact:** Medium - Reduces frontend complexity and edge case handling

---

### 11. Add Data Export Capabilities

**Description:**
Users cannot download readings for offline analysis in spreadsheet applications. Export functionality is commonly expected for utility data.

**Recommended Steps:**
1. Add `GET /api/readings/property/{property_id}/export`:
   - Query params: `format` (csv, xlsx), `start_date`, `end_date`
   - Return file download with appropriate Content-Type
2. Add `python-xlsx` or similar library for Excel export
3. For CSV, use built-in `csv` module with `StreamingResponse`
4. Include columns: timestamp, meter_name, meter_type, value, recorded_by
5. Add rate limiting to prevent abuse of expensive export operations
6. Add tests for export format correctness

**Effort:** Medium (1 day)
**Impact:** Medium - Enables offline analysis and reporting workflows

---

### 12. Add Dashboard Summary Endpoint

**Description:**
Users must make multiple API calls to get an overview of their account. A dashboard endpoint would improve initial load performance and user experience.

**Recommended Steps:**
1. Add `GET /api/users/me/dashboard` returning:
   ```python
   {
       "properties_count": 5,
       "meters_count": 23,
       "readings_this_month": 150,
       "latest_reading_date": "2024-01-15T10:30:00Z",
       "properties_summary": [
           {"id": 1, "name": "Main Office", "meters_count": 5, "latest_reading": "..."}
       ]
   }
   ```
2. Create `DashboardResponse` schema
3. Optimize with single efficient query (avoid N+1)
4. Consider caching for performance
5. Add tests

**Effort:** Medium (1 day)
**Impact:** Medium - Improves UX and reduces API calls on app load

---

### 13. Production Security and Monitoring

**Description:**
Add security measures and monitoring capabilities to make the deployment production-ready for real users.

**Recommended Steps:**
1. Add rate limiting using `slowapi` package
   - Install: `uv add slowapi`
   - Configure limits per endpoint (e.g., 100 requests/minute for auth)
2. Configure CORS middleware for frontend domain
   - Update `app/main.py` with `CORSMiddleware`
3. Set up error monitoring with Sentry
   - Install: `uv add sentry-sdk[fastapi]`
   - Configure DSN via `fly secrets set SENTRY_DSN="..."`
4. Add structured request logging
   - Consider `structlog` for JSON logging
5. Test security measures locally before deploying

**Effort:** Low (1-2 hours)
**Impact:** Medium - Improves security posture and observability. Important for production use.

**Dependencies:** Core Fly.io Deployment should be completed first.

---

## Low Priority

### 14. Add Request ID Tracking

**Description:**
No correlation IDs exist for tracking requests through logs. Makes debugging and support requests difficult.

**Recommended Steps:**
1. Add middleware to generate/extract `X-Request-ID` header
2. Include request ID in all log messages
3. Return request ID in error responses for support reference
4. Consider adding `X-Request-ID` to successful responses too
5. Update logging configuration to include request context

**Effort:** Low (3-4 hours)
**Impact:** Low - Developer/ops quality of life, not end-user visible

---

### 15. Explicit Timezone Handling

**Description:**
`reading_timestamp` accepts naive datetimes without timezone information. This can cause confusion and data inconsistencies for multi-timezone deployments.

**Recommended Steps:**
1. Update schemas to require timezone-aware datetimes or assume UTC
2. Add validation to reject naive datetimes (or auto-convert to UTC)
3. Store all timestamps in UTC in database
4. Document timezone expectations in API docs
5. Consider adding user timezone preference for display formatting

**Effort:** Medium (1 day)
**Impact:** Low - Important for correctness but may not affect single-timezone deployments

---

### 16. Deployment Documentation

**Description:**
Update project documentation to include deployment instructions, environment variable reference, and troubleshooting guide.

**Recommended Steps:**
1. Update `README.md` with deployment section
   - Quick start commands for Fly.io
   - Link to detailed plan document
2. Document all environment variables in a table format
   - Required vs optional
   - Production vs development defaults
3. Add troubleshooting guide for common issues
   - Database connection errors
   - Health check failures
   - Volume mounting issues
4. Add architecture diagram showing Fly.io components

**Effort:** Low (30 minutes - 1 hour)
**Impact:** Low-Medium - Improves developer experience and reduces onboarding time.

---

### 17. Add Webhook/Event System

**Description:**
Users cannot be notified when readings are submitted or when anomalies are detected. Webhooks enable integrations with external systems.

**Recommended Steps:**
1. Create `Webhook` model (url, events, secret, is_active)
2. Add CRUD endpoints for webhook management
3. Implement async webhook delivery (background task or queue)
4. Support events: `reading.created`, `reading.bulk_created`, `meter.created`
5. Include HMAC signature for webhook verification
6. Add retry logic for failed deliveries
7. Add webhook delivery logs

**Effort:** High (3-5 days)
**Impact:** Low-Medium - Enables integrations but not core functionality

---

## Future Enhancements

### 18. SQLite to Postgres Migration Path

**Description:**
When the application outgrows SQLite (write contention, need for replicas), migrate to Fly Postgres.

**Recommended Steps:**
1. Create Fly Postgres cluster: `fly postgres create --name electric-db`
2. Write data migration script (SQLite → Postgres)
3. Attach database to app: `fly postgres attach electric-db`
4. Update SQLAlchemy models for Postgres compatibility (if needed)
5. Test thoroughly in staging environment
6. Execute migration during low-traffic period

**Effort:** Medium (3-4 hours)
**Impact:** Medium - Enables horizontal scaling and higher write throughput. Only needed when traffic justifies the additional ~$15/month cost.

**Trigger Conditions:**
- SQLite write contention observed
- Need for read replicas
- Traffic exceeds single-instance capacity

---

### 19. Multi-Region Deployment

**Description:**
Deploy to multiple Fly.io regions for lower latency and higher availability.

**Recommended Steps:**
1. Identify target regions based on user distribution
2. Scale to multiple machines: `fly scale count 2 --region iad,lhr`
3. If using Postgres, configure read replicas in each region
4. Update health checks for multi-region awareness
5. Monitor latency improvements

**Effort:** Medium (2-3 hours)
**Impact:** Low-Medium - Improves latency for geographically distributed users. Increases cost proportionally.

**Dependencies:** Core deployment and CI/CD must be completed. Consider after validating single-region performance.

---

## Summary

| # | Task | Priority | Effort | Impact |
|---|------|----------|--------|--------|
| 1 | Auth enforcement on endpoints | Critical | Medium | High |
| 2 | Value validation on readings | Critical | Low | High |
| 3 | Core Fly.io deployment | Critical | Low | High |
| 4 | Pagination metadata on lists | High | Low | High |
| 5 | Search/filter capabilities | High | Medium | High |
| 6 | User profile endpoints | High | Medium | High |
| 7 | Date range queries | High | Medium | High |
| 8 | CI/CD pipeline | High | Low | Medium-High |
| 9 | Soft delete endpoints | Medium | Low | Medium |
| 10 | Normalize empty responses | Medium | Low | Medium |
| 11 | Data export capabilities | Medium | Medium | Medium |
| 12 | Dashboard summary endpoint | Medium | Medium | Medium |
| 13 | Production hardening | Medium | Low | Medium |
| 14 | Request ID tracking | Low | Low | Low |
| 15 | Explicit timezone handling | Low | Medium | Low |
| 16 | Deployment documentation | Low | Low | Low-Medium |
| 17 | Webhook/event system | Low | High | Low-Medium |
| 18 | Postgres migration | Future | Medium | Medium |
| 19 | Multi-region deployment | Future | Medium | Low-Medium |

---

## Notes

- All effort estimates assume familiarity with the codebase and tools
- Fly.io costs are estimated at $2-5/month for the recommended configuration
- See `docs/FLYIO_INTEGRATION_PLAN.md` for detailed Fly.io implementation specifications

---

*Last updated: 2025-01-26*
