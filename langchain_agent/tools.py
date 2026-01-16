from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Any, Optional
from browser_use.browser.session import BrowserSession


class OpenURLInput(BaseModel):
    url: str = Field(..., description="The URL to navigate to")


class OpenURLTool(BaseTool):
    name: str = "open_url"
    description: str = "Open a URL in the browser"
    args_schema: type[BaseModel] = OpenURLInput
    session: Optional[BrowserSession] = Field(exclude=True, default=None)

    def __init__(self, session: BrowserSession, **kwargs: Any):
        super().__init__(session=session, **kwargs)

    async def _arun(self, url: str) -> str:
        """Navigate to a URL."""
        if not self.session:
            return "Error: Browser session not initialized"
        # Ensure browser is started
        if not self.session.agent_focus_target_id:
            await self.session.start()
        
        # Navigate to URL
        await self.session.navigate_to(url)
        return f"Successfully navigated to {url}"
    
    def _run(self, url: str) -> str:
        """Synchronous wrapper for async navigation."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self._arun(url))
                    return future.result()
            return loop.run_until_complete(self._arun(url))
        except RuntimeError:
            return asyncio.run(self._arun(url))


class ObserveDOMInput(BaseModel):
    unused: str = Field(default="", description="Optional parameter (not used)")

class ObserveDOMTool(BaseTool):
    name: str = "observe_dom"
    description: str = "Observe and summarize the current DOM"
    args_schema: type[BaseModel] = ObserveDOMInput
    session: Optional[BrowserSession] = Field(exclude=True, default=None)

    def __init__(self, session: BrowserSession, **kwargs: Any):
        super().__init__(session=session, **kwargs)

    async def _arun(self, unused: str = "") -> str:
        """Observe and summarize the current DOM state."""
        if not self.session:
            return "Error: Browser session not initialized"
        # Ensure browser is started
        if not self.session.agent_focus_target_id:
            await self.session.start()
        
        # Get browser state summary
        state = await self.session.get_browser_state_summary(include_screenshot=False)
        
        # Format the state as a readable string
        result_parts = [
            f"URL: {state.url}",
            f"Title: {state.title}",
        ]
        
        if state.dom_state and state.dom_state.selector_map:
            result_parts.append(f"\nInteractive Elements ({len(state.dom_state.selector_map)}):")
            result_parts.append("Use the EXACT index numbers shown below - they do NOT start from 0!")
            result_parts.append("")
            
            # Check if we're on a search results page or product page
            is_search_page = '/s?' in state.url or 'k=' in state.url
            is_product_page = '/dp/' in state.url or '/gp/product/' in state.url
            
            # Separate elements by type
            product_links = []
            add_to_cart_buttons = []
            other_elements = []
            
            for index, element in list(state.dom_state.selector_map.items()):
                href = element.attributes.get('href', '')
                text = element.get_all_children_text(max_depth=3)[:200]
                text_lower = text.lower() if text else ''
                
                # Check if this is a product link (on search pages)
                if is_search_page and element.tag_name == 'a' and href and ('/dp/' in href or '/gp/product/' in href):
                    product_links.append((index, element, text))
                # Check if this is an "Add to Cart" button (on product pages)
                elif is_product_page:
                    # Check by text content
                    is_add_to_cart = any(keyword in text_lower for keyword in [
                        'add to cart', 'add to basket', 'add to bag', 'buy now',
                        'add to shopping cart', 'add item to cart'
                    ])
                    # Check by ID/name attributes
                    elem_id = element.attributes.get('id', '').lower()
                    elem_name = element.attributes.get('name', '').lower()
                    is_add_to_cart = is_add_to_cart or any(keyword in elem_id or keyword in elem_name for keyword in [
                        'add-to-cart', 'addtocart', 'add-to-basket', 'buy-now', 'add-to-bag'
                    ])
                    # Check by aria-label
                    aria_label = element.attributes.get('aria-label', '').lower()
                    is_add_to_cart = is_add_to_cart or any(keyword in aria_label for keyword in [
                        'add to cart', 'add to basket', 'buy now'
                    ])
                    
                    if is_add_to_cart and element.tag_name in ['button', 'input', 'span', 'a', 'div']:
                        add_to_cart_buttons.append((index, element, text))
                    else:
                        other_elements.append((index, element))
                else:
                    other_elements.append((index, element))
            
            # Show product links first if we're on a search page
            if is_search_page and product_links:
                result_parts.append("✅ PRODUCT LINKS (click these to view products):")
                for index, element, text in product_links[:20]:  # Show first 20 product links
                    href = element.attributes.get('href', '')
                    elem_info = f"  [{index}] {element.tag_name} href='{href[:80]}'"
                    if text and len(text) > 10:
                        elem_info += f" text='{text[:150]}'"
                    result_parts.append(elem_info)
                result_parts.append("")
                result_parts.append("Other interactive elements:")
            
            # Show Add to Cart buttons first if we're on a product page
            if is_product_page and add_to_cart_buttons:
                result_parts.append("⭐ ADD TO CART BUTTONS (click these to add product to cart):")
                for index, element, text in add_to_cart_buttons:
                    elem_info = f"  [{index}] {element.tag_name}"
                    if element.attributes.get('id'):
                        elem_info += f" id='{element.attributes['id']}'"
                    if element.attributes.get('name'):
                        elem_info += f" name='{element.attributes['name']}'"
                    if text:
                        elem_info += f" text='{text[:150]}'"
                    result_parts.append(elem_info)
                result_parts.append("")
                result_parts.append("Other interactive elements:")
            
            # Show other elements (limit appropriately)
            if is_product_page and add_to_cart_buttons:
                limit = 100  # Show fewer other elements if we found Add to Cart buttons
            elif is_search_page and product_links:
                limit = 100
            else:
                limit = 150
            
            for index, element in other_elements[:limit]:
                elem_info = f"  [{index}] {element.tag_name}"
                if element.attributes.get('role'):
                    elem_info += f" role={element.attributes['role']}"
                if element.attributes.get('type'):
                    elem_info += f" type={element.attributes['type']}"
                if element.attributes.get('id'):
                    elem_id = element.attributes['id']
                    if 'cart' in elem_id.lower() or 'buy' in elem_id.lower():
                        elem_info += f" id='{elem_id}' ⚠️ (might be cart-related)"
                    else:
                        elem_info += f" id='{element.attributes['id']}'"
                href = element.attributes.get('href', '')
                if href:
                    if len(href) > 80:
                        href = href[:77] + "..."
                    elem_info += f" href='{href}'"
                text = element.get_all_children_text(max_depth=2)[:100]
                if text:
                    elem_info += f" text='{text}'"
                if element.attributes.get('placeholder'):
                    elem_info += f" placeholder='{element.attributes['placeholder']}'"
                result_parts.append(elem_info)
            
            # If no product links found on search page, suggest scrolling
            if is_search_page and not product_links:
                result_parts.append("")
                result_parts.append("⚠️ No product links found in visible area. Try scrolling down to see product listings.")
            
            # If no Add to Cart button found on product page, provide guidance
            if is_product_page and not add_to_cart_buttons:
                result_parts.append("")
                result_parts.append("⚠️ No 'Add to Cart' button found. Look for buttons with text containing 'cart', 'basket', 'buy', or 'add'. You may need to select product options (size, color, quantity) first.")
        
        return "\n".join(result_parts)
    
    def _run(self, unused: str = "") -> str:
        """Synchronous wrapper for async observation."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, create a task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self._arun(unused))
                    return future.result()
            return loop.run_until_complete(self._arun(unused))
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(self._arun(unused))


class ClickElementInput(BaseModel):
    element_index: int = Field(..., description="The index of the element to click")

class ClickTool(BaseTool):
    name: str = "click_element"
    description: str = "Click an element by index"
    args_schema: type[BaseModel] = ClickElementInput
    session: Optional[BrowserSession] = Field(exclude=True, default=None)

    def __init__(self, session: BrowserSession, **kwargs: Any):
        super().__init__(session=session, **kwargs)

    async def _arun(self, element_index: int) -> str:
        """Click an element by index."""
        from browser_use.browser.events import ClickElementEvent
        
        if not self.session:
            return "Error: Browser session not initialized"
        # Ensure browser is started
        if not self.session.agent_focus_target_id:
            await self.session.start()
        
        # Get element node by index
        element_node = await self.session.get_dom_element_by_index(element_index)
        if not element_node:
            return f"Element with index {element_index} not found"
        
        # Dispatch ClickElementEvent
        event = self.session.event_bus.dispatch(ClickElementEvent(node=element_node))
        await event
        await event.event_result(raise_if_any=True, raise_if_none=False)
        
        return f"Successfully clicked element {element_index}"
    
    def _run(self, element_index: int) -> str:
        """Synchronous wrapper for async clicking."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self._arun(element_index))
                    return future.result()
            return loop.run_until_complete(self._arun(element_index))
        except RuntimeError:
            return asyncio.run(self._arun(element_index))


class TypeTextInput(BaseModel):
    element_index: int = Field(..., description="The index of the input element")
    text: str = Field(..., description="The text to type into the input field")

class TypeTool(BaseTool):
    name: str = "type_text"
    description: str = "Type text into an input field using element index"
    args_schema: type[BaseModel] = TypeTextInput
    session: Optional[BrowserSession] = Field(exclude=True, default=None)

    def __init__(self, session: BrowserSession, **kwargs: Any):
        super().__init__(session=session, **kwargs)

    async def _arun(self, element_index: int, text: str) -> str:
        """Type text into an input field by element index."""
        from browser_use.browser.events import TypeTextEvent
        
        if not self.session:
            return "Error: Browser session not initialized"
        # Ensure browser is started
        if not self.session.agent_focus_target_id:
            await self.session.start()
        
        # Get element node by index
        element_node = await self.session.get_dom_element_by_index(element_index)
        if not element_node:
            return f"Element with index {element_index} not found"
        
        # Dispatch TypeTextEvent
        event = self.session.event_bus.dispatch(
            TypeTextEvent(node=element_node, text=text, clear=True)
        )
        await event
        result = await event.event_result(raise_if_any=True, raise_if_none=False)
        
        return f"Successfully typed '{text}' into element {element_index}"
    
    def _run(self, element_index: int, text: str) -> str:
        """Synchronous wrapper for async typing."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, create a task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self._arun(element_index, text))
                    return future.result()
            return loop.run_until_complete(self._arun(element_index, text))
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(self._arun(element_index, text))


class ScrollInput(BaseModel):
    down: bool = Field(default=True, description="Scroll down (True) or up (False)")
    pages: float = Field(default=1.0, description="Number of pages to scroll (e.g., 1.0, 0.5, 2.0)")

class ScrollTool(BaseTool):
    name: str = "scroll"
    description: str = "Scroll the page up or down by a number of pages"
    args_schema: type[BaseModel] = ScrollInput
    session: Optional[BrowserSession] = Field(exclude=True, default=None)

    def __init__(self, session: BrowserSession, **kwargs: Any):
        super().__init__(session=session, **kwargs)

    async def _arun(self, down: bool = True, pages: float = 1.0) -> str:
        """Scroll the page."""
        from browser_use.browser.events import ScrollEvent
        
        if not self.session:
            return "Error: Browser session not initialized"
        # Ensure browser is started
        if not self.session.agent_focus_target_id:
            await self.session.start()
        
        # Calculate scroll amount in pixels (approximately 1000px per page)
        scroll_pixels = int(pages * 1000)
        
        # Dispatch ScrollEvent
        event = self.session.event_bus.dispatch(
            ScrollEvent(direction='down' if down else 'up', amount=scroll_pixels)
        )
        await event
        
        direction_str = "down" if down else "up"
        return f"Successfully scrolled {direction_str} by {pages} page(s)"
    
    def _run(self, down: bool = True, pages: float = 1.0) -> str:
        """Synchronous wrapper for async scrolling."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self._arun(down, pages))
                    return future.result()
            return loop.run_until_complete(self._arun(down, pages))
        except RuntimeError:
            return asyncio.run(self._arun(down, pages))
