# TODO - Fixing and Setting up Local Development Environment

## Phase 1: Fix Core Application Issues
- [ ] Fix app/__init__.py import conflict with config
- [ ] Update session configuration for local development
- [ ] Make APScheduler optional for local dev
- [ ] Fix Redis client compatibility in local mode

## Phase 2: Create Required Directories
- [ ] Create logs/ directory
- [ ] Create download_cache/ directory
- [ ] Create app/files/ directory with RSA keys

## Phase 3: Install Dependencies
- [ ] Install all required Python packages
- [ ] Verify package compatibility

## Phase 4: Initialize Database
- [ ] Create SQLite database
- [ ] Create tables
- [ ] Create test admin user

## Phase 5: Test and Run
- [ ] Run the start_local.sh script
- [ ] Verify server is accessible at http://localhost:3003

