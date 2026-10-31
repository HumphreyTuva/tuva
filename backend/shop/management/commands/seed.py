from pathlib import Path
from django.core.files import File
from django.core.management.base import BaseCommand
from shop.models import Product
D = Path(__file__).resolve().parents[4] / "frontend" / "public" / "products"
ROWS = [("ProBook 14","14\" Business Laptop","business",45000,52000,["14\" FHD","16GB RAM","512GB SSD"],"probook.png","Best seller",40),
 ("UltraBook 15","15.6\" Ultrabook","ultrabooks",58000,65000,["15.6\" FHD","16GB RAM","512GB SSD"],"ultrabook.png","Great value",25),
 ("GamePro 16","16\" Gaming Laptop","gaming",180000,205000,["16\" QHD","16GB RAM","1TB SSD","RTX 4060"],"gamepro.png","High performance",12),
 ("Flex 2-in-1","14\" 2-in-1 Laptop","2-in-1",72000,85000,["14\" FHD Touch","16GB RAM","512GB SSD"],"flex.png","2-in-1",0)]
class Command(BaseCommand):
    def handle(self, *a, **k):
        for n,s,c,price,compare,sp,img,b,st in ROWS:
            if not Product.objects.filter(name=n).exists():
                p = Product(name=n,subtitle=s,category=c,price=price,compare_price=compare,specs=sp,badge=b,stock=st)
                with open(D/img,"rb") as f: p.image.save(img, File(f), save=True)
