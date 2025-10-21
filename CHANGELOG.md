
# Change Log

---

## 0.3.6 (October 20, 2025)

Notes:
* Renamed "My Books" to "Wishlist" to improve clarity on the purpose of the page
* Add a back button to the book details page
* Clean up the latest deal page format, so the list format is identical to the all books page 
* In Book details, title is now selectable with copy button 
* Add exit button when prompted for retailer login
  * If retailer login is not provided, the retailer will no longer be tracked

BUG FIXES:
* Remove Whispersync pricing from unsupported regions 
* Fix issue where expired Amazon access wasn't being updated correctly 

---

## 0.3.5 (October 10, 2025)

Notes:
* Added the ability to view owned books (GUI Only)
* Audible Whispersync now supported for wishlists
* Ability to select if user is active audible plus member
  * If user is not an active member, no longer show audible plus books as free
* Hardcover.app support for TBR exports

BUG FIXES:
* Fixed issue where whispersync pricing wouldn't show if user owned kindle book and was NOT an audible member
* Fixed gui book filter when searching by author

---

## 0.3.4 (October 3, 2025)

Notes:
* Added whispersync pricing to Audible
  * Works on owned books and Kindle Unlimited books (if you're a Kindle Unlimited member)
* Audible books now show as free if they are in the Audible plus catalog
* Kindle books now show as free if they are in the Kindle Unlimited catalog
  * Requirement: You must be a member and marked that you are in settings 
* Reduced frequency required to re-authenticate with Libro.FM
* Reduced frequency required to re-authenticate with Chirp

---

## 0.3.3 (September 10, 2025)

Notes: 
* Improved updater for Mac app

BUG FIXES:
* Fixed Mac app cert 
* Fixed issue where pricing graph points were running off graph 

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

