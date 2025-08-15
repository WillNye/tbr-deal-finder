
# Change Log

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

