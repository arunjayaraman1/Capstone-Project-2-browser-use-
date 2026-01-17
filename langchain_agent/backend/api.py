from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn
import sys
from pathlib import Path

# Add parent directory to path to import automation module
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from automation import add_to_cart, GroceryCart

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
    items: list[str] = Field(..., description="List of product names to search and add to cart")


class AddToCartResponse(BaseModel):
    success: bool
    message: str
    cart: Optional[GroceryCart] = None
    error: Optional[str] = None


@app.get("/")
async def root():
    return {"message": "Amazon Cart API is running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/add-to-cart", response_model=AddToCartResponse)
async def add_to_cart_endpoint(request: AddToCartRequest):
    """
    Search for products on Amazon.in and add them to cart.
    Returns structured data about the items added.
    """
    try:
        if not request.items:
            raise HTTPException(status_code=400, detail="Items list cannot be empty")
        
        # Run the agent
        result = await add_to_cart(request.items)
        
        # Extract structured output
        if result and result.structured_output:
            cart = result.structured_output
            return AddToCartResponse(
                success=True,
                message=f"Successfully processed {len(cart.items)} item(s)",
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
