import hemnet
import db
import time

i = 0
while True:
    urls = db.get_pending_urls(n=100, random=True, live=True)
    if len(urls) == 0:
        print("No more pending urls. Sleeping for 60 seconds...")
        time.sleep(60)

    print(f"Getting {len(urls)} listings...")
    for item in urls:
        raw_listing = hemnet.get_single_listing(item["url"])
        if raw_listing is None:
            print(f"Failed to get {item['url']}")
            continue

        raw_listing["url"] = item["url"]
        print(f"Done with {item['url']} - iteration {i}")

        db.write_raw_listing(raw_listing, live=True)

        coords = None
        tries = 0

        while coords is None:
            coords = hemnet.get_coords(item["url"])
            if coords is None:
                print(f"Failed to get coords for url {item['url']}")
                time.sleep(2)

            tries += 1
            if tries > 5:
                break

        db.write_raw_listing_coord(item["url"], coords, live=True)
        db.marks_urls_as_done(urls=[item["url"]])
        i += 1
