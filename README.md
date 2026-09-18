# WiFi File Transfer

A local file-transfer website for moving files between a PC and a phone/tablet over the same WiFi.

## Start
1. Install Python 3.
2. Double-click start.bat.
3. The console prints an address such as http://192.168.1.100:8765.
4. Connect the phone to the same WiFi.
5. Open that address on the phone.
6. Upload or download files.

Files stay in the local uploads folder. No cloud storage is used.

## Windows Firewall
If the phone cannot connect, allow Python through Windows Firewall on your Private network, or run this in PowerShell as Administrator:

New-NetFirewallRule -DisplayName "WiFi File Transfer 8765" -Direction Inbound -Protocol TCP -LocalPort 8765 -Action Allow -Profile Private

## Security
This is intended for a trusted local network. Do not expose port 8765 directly to the internet.

Uploads are limited to 5 GB per request.
