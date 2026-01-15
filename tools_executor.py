"""  
Tool Executors - Implements actual Mac and browser automation
Translates agent's tool calls into real actions
"""

import subprocess
import time
from typing import Dict, Any, Optional
from loguru import logger
import pyautogui
from playwright.async_api import async_playwright
import asyncio

try:
    from PyXA import *
    PYXA_AVAILABLE = True
except ImportError:
    logger.warning("PyXA not available - some Mac automation features will be limited")
    PYXA_AVAILABLE = False


class ToolExecutor:
    """
    Executes tools requested by the agent
    Handles Mac automation, browser automation, and messaging
    """
    
    def __init__(self):
        self.browser = None
        self.browser_page = None
        self.playwright = None
        
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main execution dispatcher - routes to appropriate handler
        """
        logger.info(f"Executing tool: {tool_name} with params: {parameters}")
        
        try:
            if tool_name == "mac_open_app":
                return await self._mac_open_app(parameters)
            elif tool_name == "mac_type_text":
                return await self._mac_type_text(parameters)
            elif tool_name == "mac_press_key":
                return await self._mac_press_key(parameters)
            elif tool_name == "browser_navigate":
                return await self._browser_navigate(parameters)
            elif tool_name == "browser_click":
                return await self._browser_click(parameters)
            elif tool_name == "browser_type":
                return await self._browser_type(parameters)
            elif tool_name == "send_message":
                return await self._send_message(parameters)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
                
        except Exception as e:
            logger.error(f"Error executing {tool_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ===== MAC AUTOMATION TOOLS =====
    
    async def _mac_open_app(self, params: Dict) -> Dict:
        """
        Open a Mac application
        """
        app_name = params.get("app_name")
        logger.info(f"Opening Mac app: {app_name}")
        
        try:
            if PYXA_AVAILABLE:
                # Use PyXA for cleaner app control
                app = Application(app_name)
                app.activate()
            else:
                # Fallback to AppleScript
                script = f'tell application "{app_name}" to activate'
                subprocess.run(["osascript", "-e", script], check=True)
            
            time.sleep(1)  # Give app time to open
            
            return {
                "success": True,
                "message": f"Opened {app_name}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to open {app_name}: {e}"
            }
    
    async def _mac_type_text(self, params: Dict) -> Dict:
        """
        Type text in the currently focused application
        """
        text = params.get("text")
        logger.info(f"Typing text: {text[:50]}...")
        
        try:
            # Use pyautogui for typing
            pyautogui.typewrite(text, interval=0.05)
            
            return {
                "success": True,
                "message": f"Typed {len(text)} characters"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to type text: {e}"
            }
    
    async def _mac_press_key(self, params: Dict) -> Dict:
        """
        Press a keyboard key
        """
        key = params.get("key")
        logger.info(f"Pressing key: {key}")
        
        try:
            pyautogui.press(key)
            
            return {
                "success": True,
                "message": f"Pressed {key}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to press {key}: {e}"
            }
    
    # ===== BROWSER AUTOMATION TOOLS =====
    
    async def _ensure_browser(self):
        """
        Ensure browser is initialized
        """
        if not self.browser:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=False)
            self.browser_page = await self.browser.new_page()
    
    async def _browser_navigate(self, params: Dict) -> Dict:
        """
        Navigate browser to a URL
        """
        url = params.get("url")
        logger.info(f"Navigating to: {url}")
        
        try:
            await self._ensure_browser()
            
            # Add protocol if missing
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            
            await self.browser_page.goto(url)
            await self.browser_page.wait_for_load_state('networkidle')
            
            return {
                "success": True,
                "message": f"Navigated to {url}",
                "url": url
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to navigate: {e}"
            }
    
    async def _browser_click(self, params: Dict) -> Dict:
        """
        Click an element on the page
        """
        selector = params.get("selector")
        logger.info(f"Clicking element: {selector}")
        
        try:
            await self._ensure_browser()
            await self.browser_page.click(selector)
            
            return {
                "success": True,
                "message": f"Clicked {selector}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to click: {e}"
            }
    
    async def _browser_type(self, params: Dict) -> Dict:
        """
        Type text into a browser input field
        """
        selector = params.get("selector")
        text = params.get("text")
        logger.info(f"Typing into {selector}: {text[:50]}...")
        
        try:
            await self._ensure_browser()
            await self.browser_page.fill(selector, text)
            
            return {
                "success": True,
                "message": f"Typed into {selector}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to type: {e}"
            }
    
    # ===== MESSAGING TOOLS =====
    
    async def _send_message(self, params: Dict) -> Dict:
        """
        Send a message via messaging app
        """
        app = params.get("app")
        recipient = params.get("recipient")
        message = params.get("message")
        
        logger.info(f"Sending message via {app} to {recipient}")
        
        try:
            if app.lower() == "imessage":
                return await self._send_imessage(recipient, message)
            elif app.lower() == "whatsapp":
                return await self._send_whatsapp(recipient, message)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported messaging app: {app}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to send message: {e}"
            }
    
    async def _send_imessage(self, recipient: str, message: str) -> Dict:
        """
        Send iMessage using AppleScript
        """
        try:
            script = f'''
            tell application "Messages"
                set targetService to 1st service whose service type = iMessage
                set targetBuddy to buddy "{recipient}" of targetService
                send "{message}" to targetBuddy
            end tell
            '''
            
            subprocess.run(["osascript", "-e", script], check=True)
            
            return {
                "success": True,
                "message": f"Sent iMessage to {recipient}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to send iMessage: {e}"
            }
    
    async def _send_whatsapp(self, recipient: str, message: str) -> Dict:
        """
        Send WhatsApp message (requires WhatsApp Desktop)
        """
        try:
            # Open WhatsApp
            await self._mac_open_app({"app_name": "WhatsApp"})
            time.sleep(2)
            
            # Use keyboard shortcut to open new chat
            pyautogui.hotkey('command', 'n')
            time.sleep(1)
            
            # Type recipient name
            pyautogui.typewrite(recipient, interval=0.1)
            time.sleep(1)
            
            # Select first result
            pyautogui.press('return')
            time.sleep(1)
            
            # Type and send message
            pyautogui.typewrite(message, interval=0.05)
            pyautogui.press('return')
            
            return {
                "success": True,
                "message": f"Sent WhatsApp message to {recipient}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to send WhatsApp: {e}"
            }
    
    async def cleanup(self):
        """
        Clean up resources
        """
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()