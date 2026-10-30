from pathlib import Path
from django.core.files import File
from django.core.management.base import BaseCommand
from shop.models import Product
D = Path(__file__).resolve().parents[4] / "frontend" / "public" / "products"
ROWS = [("ProBook 14","14\" Business Laptop","business",679,799,4.8,["14\" FHD","16GB RAM","512GB SSD"],"probook.png","Best seller",40),
 ("UltraBook 15","15.6\" Ultrabook","ultrabooks",729,879,4.7,["15.6\" FHD","16GB RAM","512GB SSD"],"ultrabook.png","Great value",25),
 ("GamePro 16","16\" Gaming Laptop","gaming",1159,1329,4.8,["16\" QHD","16GB RAM","1TB SSD","RTX 4060"],"gamepro.png","High performance",12),
 ("Flex 2-in-1","14\" 2-in-1 Laptop","2-in-1",829,979,4.6,["14\" FHD Touch","16GB RAM","512GB SSD"],"flex.png","2-in-1",0)]
class Command(BaseCommand):
    def handle(self, *a, **k):
        for n,s,c,lo,hi,r,sp,img,b,st in ROWS:
            if not Product.objects.filter(name=n).exists():
                p = Product(name=n,subtitle=s,category=c,price_min=lo,price_max=hi,rating=r,specs=sp,badge=b,stock=st)
                with open(D/img,"rb") as f: p.image.save(img, File(f), save=True)
