import asyncio

from pydantic import BaseModel, Field

from browser_use import Agent, Browser, ChatOpenAI


class GroceryItem(BaseModel):
	"""A single grocery item"""

	name: str = Field(..., description='Item name')
	price: float = Field(..., description='Price as number')
	brand: str | None = Field(None, description='Brand name')
	size: str | None = Field(None, description='Size or quantity')
	url: str = Field(..., description='Full URL to item')


class GroceryCart(BaseModel):
	"""Product detail page"""

	items: list[GroceryItem] = Field(default_factory=list, description='All grocery items found')


async def add_to_cart(items: list[str] = []):
	browser = Browser(headless=False)

	llm = ChatOpenAI(model="gpt-4o-mini")

	# Task prompt
	task = f"""
    Go to https://www.amazon.in
    Wait for the page to fully load.

    STEP-BY-STEP PROCESS:
    0. SEARCH ON AMAZON (CRITICAL - DO THIS FIRST):
       a) Find the search input box (usually has id="twotabsearchtextbox" or placeholder like "Search Amazon.in")
       b) Use the INPUT action (NOT click) to type "{items[0] if items else 'product'}" into the search input box
       c) After typing, click the search button (usually a magnifying glass icon or "Go" button) OR use send_keys with "Enter" to submit
       d) Wait for search results page to load completely (URL should change to include /s?k=)
       e) Verify you are on the search results page before proceeding
    1. Once on search results page, use the extract action to list first 10 products on the page with their COMPLETE product URLs (full URL starting with https://), product names, prices, brands (if visible), sizes (if visible), and identify which ones are "Sponsored" and which are NOT sponsored.
    2. From the extracted list, identify the first product that:
       - Is NOT marked as "Sponsored"
       - Has a product name that matches or closely matches "{items[0] if items else 'product'}" (the search term)
       - Note its complete URL
    3. Scroll down if needed to see all products clearly.
    4. ALTERNATIVE METHODS TO OPEN PRODUCT (try in this order):
       a) FIRST TRY (MOST RELIABLE): Use navigate action with the complete product URL you extracted
       b) IF navigate doesn't work: Use evaluate action with JavaScript to find and click the link by URL
       c) IF evaluate doesn't work: Use find_text action to scroll to the product name, then try click action
       d) LAST RESORT: Use send_keys with multiple "Tab" presses followed by "Enter" for keyboard navigation
    5. Wait for the product detail page to fully load (verify URL changed to product page).
    6. Extract the product details from the product detail page using extract action:
       - Product name
       - Price (as a number, not text)
       - Brand (if available)
       - Size/quantity (if available)
       - Current page URL
    7. Add the product to cart by clicking the "Add to Cart" button ONCE.
    8. IMMEDIATELY AFTER clicking "Add to Cart", wait for the page to update (2-3 seconds) and check for SUCCESS indicators:
       - Look for "Added to cart" confirmation message or green checkmark
       - Look for cart count/badge showing items in cart (usually in top right)
       - Look for "Proceed to Buy" or "Go to Cart" buttons appearing
       - The page URL may change to include /cart/ or /gp/cart/
       - The "Add to Cart" button may disappear or become unavailable - THIS IS A SUCCESS SIGN, NOT A FAILURE
       - The page may show a confirmation page with product details - THIS IS SUCCESS, NOT AN EMPTY PAGE
       - Use extract action to check the page content if you're unsure
       - If you see ANY of these indicators, the item was successfully added - DO NOT retry
    9. CRITICAL: If the "Add to Cart" button click results in an error like "element not found" or "not interactable", but the page has changed (URL changed, new elements appeared, button disappeared), this means SUCCESS - the item was added. DO NOT retry.
    10. IMMEDIATELY after confirming the item was added to cart, use the done action with the extracted product details formatted as GroceryCart JSON. DO NOT perform any additional steps after adding to cart (no file reading, no verification, no extra extracts).

    CRITICAL RULES:
    - FOR SEARCHING: Use the INPUT action to type text into the search box. DO NOT click the search icon/button first - click it AFTER typing. The search box is usually a text input field, not a button.
    - If the input action doesn't work, try using find_text to locate the search box, then use input with the correct element index
    - NEVER click on any product that has "Sponsored" can appear as text, badge, aria-label, or small label above the title.
    - If any sponsored indicator exists, exclude the product.
    - ALWAYS use extract first to verify which products are sponsored
    - The unsponsored product should have the exact product name or closely match "{items[0] if items else 'product'}" (the product name you provided)
    - The first unsponsored product is usually after 2-4 sponsored products
    - PREFER using navigate action with the extracted product URL instead of click by index
    - If click by index fails with "element index not available", IMMEDIATELY switch to navigate with URL
    - CRITICAL: After clicking "Add to Cart", wait 2-3 seconds for the page to update, then check for success indicators.
    - If the "Add to Cart" button disappears, becomes unavailable, or shows an error like "element not found" AFTER clicking it, this usually means SUCCESS - the page changed because the item was added. Check the page content with extract to confirm.
    - If you see "Added to cart", cart count, confirmation page, or URL changed to /cart/ - THIS MEANS SUCCESS. The confirmation page is NOT an empty page - it's proof the item was added.
    - DO NOT retry adding to cart if you see success indicators OR if the button disappeared after clicking - this will add duplicate items
    - DO NOT click the add to cart button again after it's already been clicked - even if you get an error about the button not being found
    - DO NOT navigate back to the product page and try again - this will add another item
    - Once you confirm the product is added to cart (via success indicators or page change), IMMEDIATELY use the done action to complete the task
    - DO NOT perform any additional steps after adding to cart (no file reading, no verification steps, no extra extracts, no file operations)
    - The done action should include the product details (name, price, brand, size, URL) formatted as a GroceryCart with items list
    - Double-check by extracting the product list before clicking
    - For structured output, extract all product details (name, price, brand, size, URL) and return them as a list of GroceryItem objects in the GroceryCart using the done action

    ERROR RECOVERY:
    - If search doesn't work (you're still on home page after trying to search):
      * Use extract to find the search input box element
      * Use input action with the correct element index to type the search term
      * Then click the search button or use send_keys with "Enter"
      * Verify URL changed to search results page before proceeding
    - If click action fails with "element index not available" or "page may have changed":
      * IMMEDIATELY use navigate action with the product URL from your extract
      * If you don't have the URL, re-extract the product list to get the URL
      * DO NOT retry with the same index - it will fail again
    - If navigate doesn't work, use evaluate with JavaScript: (function(){{const url="PRODUCT_URL";const link=Array.from(document.querySelectorAll('a')).find(a=>a.href===url||a.href.includes(url.split('/dp/')[1]?.split('/')[0]));if(link){{link.click();return"clicked"}}return"not found"}})()
    - If product page doesn't load, use go_back and try a different product URL
    - CRITICAL ERROR RECOVERY FOR "ADD TO CART":
      * If you get an error after clicking "Add to Cart" (like "element not found", "not interactable", "page may have changed"):
        1. FIRST: Wait 2-3 seconds for the page to update
        2. Use extract action to check the current page content
        3. Look for success indicators: "Added to cart", cart count, "Proceed to Buy" button, URL changed to /cart/
        4. If you see ANY success indicator OR if the page content has changed significantly - THIS IS SUCCESS. Use done action immediately.
        5. ONLY if the page is still the same product page with the "Add to Cart" button still visible and no success indicators, then you may retry ONCE
        6. If you already clicked "Add to Cart" and the button is gone or page changed, DO NOT navigate back and try again - this adds duplicate items
      * The most common scenario: You click "Add to Cart", get an error about the button, but the page actually changed to show "Added to cart" - this is SUCCESS, not failure
    """

	# Create agent with structured output
	agent = Agent(
		browser=browser,
		llm=llm,
		task=task,
		output_model_schema=GroceryCart,
		max_steps=50,  # Limit steps to prevent infinite loops
		step_timeout=120,  # 2 minutes per step timeout
	)

	# Run the agent
	result = await agent.run()
	return result


if __name__ == '__main__':
	# Get user input
	items_input = input('What product would you like to buy?').strip()
	if not items_input:
		print('Please enter a product name')
		exit(1)
	else:
		items = [item.strip() for item in items_input.split(',')]

	result = asyncio.run(add_to_cart(items))

	# Access structured output
	if result and result.structured_output:
		cart = result.structured_output

		print(f'\n{"=" * 60}')
		print('✅ Items Added to Cart')
		print(f'{"=" * 60}\n')

		if cart.items:
			for item in cart.items:
				print(f'Name: {item.name}')
				print(f'Price: ${item.price}')
				if item.brand:
					print(f'Brand: {item.brand}')
				if item.size:
					print(f'Size: {item.size}')
				print(f'URL: {item.url}')
				print(f'{"-" * 60}')
		else:
			print('⚠️ No items were found in the cart')
	else:
		print('\n⚠️ Agent completed but no structured output was returned')
		if result:
			print(f'Number of steps: {result.number_of_steps()}')
			if result.has_errors():
				print('Errors occurred during execution')