#!/usr/bin/env python3
"""
Simple HTTP server to run the AI Gym Trainer web app
Run this script and open http://localhost:8000 in your browser
"""

import http.server
import socketserver
import webbrowser
import os

PORT = 8000

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers for local development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

def main():
    # Change to the directory where this script is located
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    Handler = MyHTTPRequestHandler
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        url = f"http://localhost:{PORT}/index.html"
        print("=" * 60)
        print("🚀 AI GYM TRAINER PRO - SERVER STARTED")
        print("=" * 60)
        print(f"📱 Open your browser and go to: {url}")
        print(f"📂 Serving files from: {os.getcwd()}")
        print("=" * 60)
        print("⌨️  Press Ctrl+C to stop the server")
        print("=" * 60)
        
        # Automatically open browser
        try:
            webbrowser.open(url)
        except:
            print("⚠️  Could not open browser automatically")
            print(f"   Please manually open: {url}")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n🛑 Server stopped. Goodbye!")
            httpd.shutdown()

if __name__ == "__main__":
    main()

