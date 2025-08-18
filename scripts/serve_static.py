#!/usr/bin/env python3
"""
serve_static.py - Simple HTTP server for local development and testing
==================================================================

Serves the aquaponics dashboard locally with proper MIME types and CORS headers.
Useful for local development, E2E testing, and debugging.

Usage:
  python3 scripts/serve_static.py [--port PORT] [--host HOST]
  
Examples:
  python3 scripts/serve_static.py                    # Serve on localhost:8000
  python3 scripts/serve_static.py --port 3000        # Serve on localhost:3000
  python3 scripts/serve_static.py --host 0.0.0.0     # Serve on all interfaces
"""

import argparse
import http.server
import socketserver
import os
import sys
from pathlib import Path


class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler with CORS headers and proper MIME types."""
    
    def end_headers(self):
        """Add CORS headers to all responses."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS preflight."""
        self.send_response(200)
        self.end_headers()
    
    def guess_type(self, path):
        """Guess MIME type with better defaults for web assets."""
        mime_type, encoding = super().guess_type(path)
        
        # Add specific MIME types for common web files
        if path.endswith('.js'):
            return 'application/javascript', encoding
        elif path.endswith('.mjs'):
            return 'application/javascript', encoding
        elif path.endswith('.css'):
            return 'text/css', encoding
        elif path.endswith('.json'):
            return 'application/json', encoding
        elif path.endswith('.woff2'):
            return 'font/woff2', encoding
        elif path.endswith('.woff'):
            return 'font/woff', encoding
        
        return mime_type, encoding
    
    def log_message(self, format, *args):
        """Log messages with timestamp."""
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = format % args
        print(f"[{timestamp}] {self.address_string()} - {message}")


def main():
    """Main entry point for static server."""
    parser = argparse.ArgumentParser(
        description="Simple HTTP server for aquaponics dashboard development",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 serve_static.py                    # Serve on localhost:8000
  python3 serve_static.py --port 3000        # Serve on localhost:3000
  python3 serve_static.py --host 0.0.0.0     # Serve on all interfaces
  
The server will serve files from the repository root directory.
Use Ctrl+C to stop the server.
        """
    )
    
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=8000,
        help='Port to serve on (default: 8000)'
    )
    
    parser.add_argument(
        '--host', '-H',
        default='localhost',
        help='Host to serve on (default: localhost)'
    )
    
    parser.add_argument(
        '--directory', '-d',
        default=None,
        help='Directory to serve (default: repository root)'
    )
    
    args = parser.parse_args()
    
    # Change to repository root if no directory specified
    if args.directory is None:
        script_dir = Path(__file__).parent
        repo_root = script_dir.parent
        os.chdir(repo_root)
        serve_dir = repo_root
    else:
        serve_dir = Path(args.directory)
        os.chdir(serve_dir)
    
    print(f"Aquaponics Dashboard - Development Server")
    print(f"=========================================")
    print(f"Serving directory: {serve_dir.absolute()}")
    print(f"Server address: http://{args.host}:{args.port}")
    print(f"Dashboard URL: http://{args.host}:{args.port}/")
    print(f"Data API: http://{args.host}:{args.port}/data.json")
    print(f"Coach API: http://{args.host}:{args.port}/coach.json")
    print()
    print("Press Ctrl+C to stop the server")
    print()
    
    # Check if index.html exists
    if not Path('index.html').exists():
        print("Warning: index.html not found in current directory")
        print("Make sure you're running from the repository root")
        print()
    
    # Check if data.json exists
    if Path('data.json').exists():
        print("✓ data.json found")
    else:
        print("⚠ data.json not found - dashboard will show empty state")
    
    # Check if coach.json exists
    if Path('coach.json').exists():
        print("✓ coach.json found")
    else:
        print("⚠ coach.json not found - coach panel will show offline")
    
    print()
    
    try:
        with socketserver.TCPServer((args.host, args.port), CORSHTTPRequestHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"Error: Port {args.port} is already in use.")
            print(f"Try a different port with --port option.")
            sys.exit(1)
        else:
            raise


if __name__ == "__main__":
    main()