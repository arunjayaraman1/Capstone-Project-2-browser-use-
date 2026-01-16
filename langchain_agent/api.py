from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional
import uvicorn
import json
import asyncio

# Import from the same directory
from gr import add_to_cart, ProductDetailPage

app = FastAPI(title="Amazon Cart API", version="1.0.0")

# Enable CORS for Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Streamlit URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AddToCartRequest(BaseModel):
    product_name: str = Field(..., description="Product name to search and add to cart")


class AddToCartResponse(BaseModel):
    success: bool
    message: str
    cart: Optional[ProductDetailPage] = None
    error: Optional[str] = None


@app.get("/")
async def root():
    return {"message": "Amazon Cart API is running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


async def stream_add_to_cart(product_name: str):
    """Async generator function that yields progress updates as the agent runs."""
    try:
        from browser_use import Agent, Browser, ChatOpenAI
        from gr import ProductDetailPage
        
        browser = Browser(headless=False)
        llm = ChatOpenAI(model="gpt-4o-mini")
        
        task = f"""
        Go to https://www.amazon.in
        Search for "{product_name}" on Amazon.in at the home page.
        Wait for search results to load completely.

        STEP-BY-STEP PROCESS:
        1. First, use the extract action to list first 10 products on the page with their COMPLETE product URLs (full URL starting with https://), product names, and identify which ones are "Sponsored" and which are NOT sponsored.
        2. From the extracted list, identify the first product that:
           - Is NOT marked as "Sponsored"
           - Has a product name that matches or closely matches "{product_name}" (the search term)
           - Note its complete URL
        3. Scroll down if needed to see all products clearly.
        4. ALTERNATIVE METHODS TO OPEN PRODUCT (try in this order):
           a) FIRST TRY (MOST RELIABLE): Use navigate action with the complete product URL you extracted
           b) IF navigate doesn't work: Use evaluate action with JavaScript to find and click the link by URL
           c) IF evaluate doesn't work: Use find_text action to scroll to the product name, then try click action
           d) LAST RESORT: Use send_keys with multiple "Tab" presses followed by "Enter" for keyboard navigation
        5. Wait for the product detail page to fully load (verify URL changed to product page).
        6. Extract the product name from the product detail page using extract action.
        7. Add the product to cart.
        8. Verify the product was added successfully.

        CRITICAL RULES:
        - NEVER click on any product that has "Sponsored" text visible anywhere near it
        - ALWAYS use extract first to verify which products are sponsored
        - The unsponsored product should have the exact product name or closely match "{product_name}" (the product name you provided)
        - The first unsponsored product is usually after 2-4 sponsored products
        - PREFER using navigate action with the extracted product URL instead of click by index
        - If click by index fails with "element index not available", IMMEDIATELY switch to navigate with URL
        - Once the product is added to cart, Never click the add to cart button again
        - Double-check by extracting the product list before clicking
        - For structured output, extract the product name from the product detail page and return it as product_name

        ERROR RECOVERY:
        - If click action fails with "element index not available" or "page may have changed":
          * IMMEDIATELY use navigate action with the product URL from your extract
          * If you don't have the URL, re-extract the product list to get the URL
          * DO NOT retry with the same index - it will fail again
        - If navigate doesn't work, use evaluate with JavaScript: (function(){{const url="PRODUCT_URL";const link=Array.from(document.querySelectorAll('a')).find(a=>a.href===url||a.href.includes(url.split('/dp/')[1]?.split('/')[0]));if(link){{link.click();return"clicked"}}return"not found"}})()
        - If product page doesn't load, use go_back and try a different product URL
        """
        
        agent = Agent(
            browser=browser,
            llm=llm,
            task=task,
            output_model_schema=ProductDetailPage,
            max_steps=50,  # Limit steps to prevent infinite loops
            step_timeout=120,  # 2 minutes per step timeout
        )
        
        yield f"data: {json.dumps({'type': 'status', 'message': '🚀 Starting agent...', 'step': 0})}\n\n"
        
        # Run agent and monitor progress
        previous_steps = 0
        agent_task = asyncio.create_task(agent.run())
        
        # Monitor progress
        while not agent_task.done():
            if hasattr(agent, 'history') and agent.history:
                current_steps = len(agent.history.history)
                if current_steps > previous_steps:
                    step_info = agent.history.history[-1]
                    previous_steps = current_steps
                    
                    # Get action info
                    action_name = "Processing..."
                    if step_info.model_output:
                        if hasattr(step_info.model_output, 'action') and step_info.model_output.action:
                            action = step_info.model_output.action[0]
                            # Action is typically a Pydantic model, get its action name from model_dump
                            action_dict = action.model_dump(exclude_none=True, mode='json') if hasattr(action, 'model_dump') else {}
                            # Action name is usually the first key in the dict
                            if action_dict:
                                action_name = list(action_dict.keys())[0] if action_dict else str(action)
                            else:
                                action_name = str(action)
                        elif hasattr(step_info.model_output, 'current_state'):
                            state = step_info.model_output.current_state
                            if hasattr(state, 'next_goal') and state.next_goal:
                                action_name = state.next_goal[:50] + "..." if len(state.next_goal) > 50 else state.next_goal
                    
                    yield f"data: {json.dumps({'type': 'progress', 'step': current_steps, 'action': action_name, 'message': f'✅ Step {current_steps} completed'})}\n\n"
            
            await asyncio.sleep(0.3)  # Check every 300ms
        
        # Get result
        result = await agent_task
        
        # Send completion
        if result and result.structured_output:
            cart = result.structured_output
            yield f"data: {json.dumps({'type': 'complete', 'success': True, 'message': f'✅ Successfully added {cart.product_name} to cart', 'cart': cart.model_dump()})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'complete', 'success': False, 'message': '⚠️ Agent completed but no structured output', 'error': 'No structured output available'})}\n\n"
            
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        yield f"data: {json.dumps({'type': 'error', 'success': False, 'message': '❌ An error occurred', 'error': error_msg})}\n\n"


@app.post("/add-to-cart")
async def add_to_cart_endpoint(request: AddToCartRequest):
    """
    Search for products on Amazon.in and add them to cart.
    Returns streaming updates with real-time progress.
    """
    if not request.product_name or not request.product_name.strip():
        raise HTTPException(status_code=400, detail="Product name cannot be empty")
    
    return StreamingResponse(
        stream_add_to_cart(request.product_name),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/add-to-cart-sync", response_model=AddToCartResponse)
async def add_to_cart_sync_endpoint(request: AddToCartRequest):
    """
    Search for products on Amazon.in and add them to cart.
    Returns structured data about the items added (synchronous version).
    """
    try:
        if not request.product_name or not request.product_name.strip():
            raise HTTPException(status_code=400, detail="Product name cannot be empty")
        
        # Run the agent
        result = await add_to_cart(request.product_name)
        
        # Extract structured output
        if result and result.structured_output:
            cart = result.structured_output
            return AddToCartResponse(
                success=True,
                message=f"Successfully added {cart.product_name} to cart",
                cart=cart
            )
        else:
            return AddToCartResponse(
                success=False,
                message="Agent completed but no structured output was returned",
                error="No structured output available"
            )
    
    except Exception as e:
        return AddToCartResponse(
            success=False,
            message="An error occurred while processing the request",
            error=str(e)
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
