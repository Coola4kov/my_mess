from PIL import Image, ImageDraw
from PIL.ImageQt import ImageQt
import io


class PictureImage:
    def __init__(self, path, desirable_width, desrable_height):
        self.path = path
        self.des_width = desirable_width
        self.des_height = desrable_height
        self.img = None
        self.raw_img = None
        self.width = None
        self.height = None
        self.upload_image()
        self.get_image_size()
        self.coef = self.width/self.height
        self.resize_image()

    def upload_raw_image(self):
        with open(self.path, 'rb') as f:
            self.raw_img = f.read()
        return self.raw_img

    def upload_image(self):
        self.img = Image.open(self.path)

    def get_image_size(self):
        self.width, self.height = self.img.size

    def resize_image(self):
        self.img = self.img.resize((self.des_width, int(self.des_height*self.coef)), Image.ANTIALIAS)
        return self.img

    def bytes_return(self):
        stream = io.BytesIO()
        self.img.save(stream, 'PNG')
        img_bytes = stream.getvalue()
        return img_bytes
