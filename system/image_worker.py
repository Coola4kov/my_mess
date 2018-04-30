from PIL import Image, ImageDraw
from PIL.ImageQt import ImageQt
import io
import base64


class PictureImage:
    def __init__(self, path, desirable_width=150, desrable_height=150):
        self.path = path
        self.img = None
        self.width = None
        self.height = None
        self.upload_image()
        self.get_image_size()
        self.coef = self.width/self.height
        self.des_width = desirable_width
        self.des_height = desrable_height
        self.resize_image()

    def upload_raw_image(self):
        with open(self.path, 'rb') as f:
            raw_img = f.read()
        return raw_img

    def upload_image(self):
        self.img = Image.open(self.path)

    def get_image_size(self):
        self.width, self.height = self.img.size

    def resize_image(self):
        self.img = self.img.resize((self.des_width, int(self.des_height*self.coef)), Image.ANTIALIAS)
        return self.img

    def cropped_bytes_return(self):
        stream = io.BytesIO()
        self.img.save(stream, 'PNG')
        img_bytes = stream.getvalue()
        return img_bytes

    def base64_encode(self):
        img_bytes = self.cropped_bytes_return()
        decoded_bytes = base64.encodebytes(img_bytes)
        return decoded_bytes.decode()

    @staticmethod
    def base64_decode(img_string):
        decoded_bytes = img_string.encode()
        img_bytes = base64.decodebytes(decoded_bytes)
        return img_bytes
