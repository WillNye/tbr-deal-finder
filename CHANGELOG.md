
# Change Log

---

## 0.3.2 (September 8, 2025)

Notes: 
* Disable nav bar buttons when performing certain operations
* Added config check to CLI location when running the desktop app for backwards compatibility
* Improved performance when retrieving "latest deals"

BUG FIXES:
* Fixed issue with scroll bar in the "all deals" page

---

## 0.3.1 (September 5, 2025)

Notes: 
* Added a GUI to serve as a desktop app
* Added retry behavior to Kindle and Libro on get_book call
* Saving all pricing info to be used for historical pricing details
* Added version checking to the CLI

BUG FIXES:
* Improvements to grouping titles in TBR 
* Fixed issue where known books were being marked as unknown if not found on a run
* Fixed bug where books not found were sometimes not added to Unknown books 
* Fixed regression on Windows devices when adding Kindle support

---

## 0.2.1 (August 25, 2025)

Notes: 
* Added Kindle Library support
  * Wishlist support is looking unlikely
    * Running into auth issues on the only viable endpoint https://www.amazon.com/kindle-reader-api 
* No longer attempting to retrieve details on books not previously found on every run
  * Full check is now performed weekly or when a change has been made to the user config

BUG FIXES:
* Failed Libro login no longer causing crash

---

## 0.2.0 (August 15, 2025)

Notes: 
* Added foundational Kindle support
  * Library support is undecided right now
    * Unable to find the endpoint
  * Wishlist support is undecided right now
    * Unable to find the endpoint 
* Improvements to title matching for Audible & Chirp 
* Improved request performance for Chirp & Libro

BUG FIXES:
* Fixed breaking import on Windows systems
* Fixed displayed discount percent

---

## 0.1.8 (August 13, 2025)

Notes: 
* Improved performance for tracking on libro
* Preparing EBook support

BUG FIXES:
* Fixed initial login issue in libro.fm

---

## 0.1.7 (July 31, 2025)

Notes: 
* tbr-deal-finder no longer shows deals on books you own in the same format.
  * Example: You own Dune on Audible so it won't show on Audible, Libro, or Chirp. It will show on Kindle (you don't own the ebook)
* Improvements when attempting to match authors
  * Chirp
  * Libro.FM
* Users no longer need to provide an export and can instead just track deals on their wishlist

BUG FIXES:
* Fixed wishlist pagination in libro.fm
* Fixed issue forcing user to go through setup twice when running the setup command 

---

## 0.1.6 (July 30, 2025)

Notes: 
* tbr-deal-finder now also tracks deals on the books in your wishlist. Works for all retailers.   

BUG FIXES:
* Fixed issue where no deals would display if libro is the only tracked audiobook retailer.
* Fixed retailer cli setup forcing a user to select at least two audiobook retailers.

---

## 0.1.5 (July 30, 2025)

Notes: 
* Added formatting to select messages to make the messages purpose clearer.

BUG FIXES:
* Fixed issue getting books from libro and chirp too aggressively
* User must now track deals for at least one retailer 

