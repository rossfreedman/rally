# Scraper Admin Interface

## Overview

The Scraper Admin Interface provides a web-based interface for running the Rally data scraping and import processes. This interface allows administrators to:

- Start and stop the scraper runner script
- Monitor real-time output from the scraping process
- Continue monitoring even after closing the browser page
- View process status and control execution

## Access

1. Navigate to the Admin Panel (`/admin`)
2. In the "Rally Data Management" section, click on "Scrape & Import"
3. This will take you to the scraper interface page (`/admin/scrape-import`)

## Features

### Real-time Output Display
- Live streaming of scraper output in a terminal-style interface
- Auto-scroll functionality (can be toggled on/off)
- Line counter showing total output lines
- Clear output button to reset the display

### Process Control
- **Start Scraper**: Initiates the scraper runner script
- **Stop Scraper**: Terminates the running scraper process
- **Clear Output**: Clears the output display

### Status Monitoring
- Real-time status indicator (Ready/Running/Stopped)
- Process ID display when running
- Start time tracking
- Automatic status updates every 5 seconds

### Background Execution
- The scraper continues running even if you close the browser page
- Process status is maintained across page refreshes
- You can return to the page to monitor progress

## Technical Details

### Routes
- `GET /admin/scrape-import` - Main scraper interface page
- `POST /api/admin/start-scraper` - Start the scraper process
- `POST /api/admin/stop-scraper` - Stop the scraper process
- `GET /api/admin/scraper-status` - Get current process status
- `GET /api/admin/scraper-output` - Stream real-time output (Server-Sent Events)

### Process Management
- Uses Python's `subprocess.Popen` to run the scraper
- Process is stored in `active_processes["scraping"]` global variable
- Output is streamed using Server-Sent Events (SSE)
- Process can be terminated gracefully or force-killed if needed

### Security
- All routes require admin authentication
- Uses the existing `@admin_required` decorator
- Process management is restricted to authenticated admin users

## Usage Instructions

1. **Starting the Scraper**:
   - Click the "Start Scraper" button
   - The process will begin and output will start streaming
   - Status indicator will change to "Running"
   - Process ID and start time will be displayed

2. **Monitoring Progress**:
   - Watch the real-time output in the terminal-style display
   - Use the auto-scroll toggle to control automatic scrolling
   - The line counter shows how many lines of output have been generated

3. **Stopping the Scraper**:
   - Click the "Stop Scraper" button to terminate the process
   - The process will be gracefully terminated
   - Status indicator will change to "Stopped"

4. **Background Monitoring**:
   - You can close the browser page and the scraper will continue running
   - Return to the page to resume monitoring
   - The status will automatically update to show if the process is still running

## Troubleshooting

### Common Issues

1. **"Scraper is already running" error**:
   - Another scraper process is already active
   - Use the stop button to terminate the existing process first

2. **"No scraper process is currently running" error**:
   - No active scraper process to stop
   - Start a new scraper process first

3. **Output not streaming**:
   - Check if the process is actually running
   - Refresh the page to re-establish the connection
   - Check browser console for JavaScript errors

4. **Process won't start**:
   - Check that the scraper runner script exists at `data/cron/scraper_runner.py`
   - Verify Python3 is available in the system PATH
   - Check server logs for detailed error messages

### Debug Information

- Process ID is displayed when running
- Start time is tracked and displayed
- Error messages are shown in the output stream
- Server logs contain detailed error information

## File Locations

- **Template**: `templates/mobile/scrape_import.html`
- **Routes**: `app/routes/admin_routes.py` (lines 4335-4489)
- **Scraper Script**: `data/cron/scraper_runner.py`
- **Admin Button**: `templates/mobile/admin.html` (line 76-79)

## Dependencies

- Flask with Server-Sent Events support
- Python subprocess module
- JavaScript EventSource API for real-time updates
- Admin authentication system
