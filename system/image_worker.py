from PIL import Image, ImageDraw
from PIL.ImageQt import ImageQt
from threading import Thread

import io
import time
import base64
import copy

from .config import *


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


class ImageWorker:
    def __init__(self, sock, message, img_parts):
        self.img_parts = img_parts
        self.sock = sock
        self.message = message
        self.whole_received_img = {}

    def handle(self, action):
        if action == IMG:
            self.img_handle()
        elif action == IMG_PARTS:
            self.img_parts_handle()

    def img_handle(self):
        self.img_parts.update({self.message.dict_message[IMG_ID]: {IMG_PCS: self.message.dict_message[IMG_PCS],
                                                                   USER_ID: self.message.dict_message[USER_ID],
                                                                   TIME: self.message.dict_message[TIME],
                                                                   IMG_SEQ: 0, IMG_DATA: []}})
        self.message.response_message_create(self.sock, OK, True, 'Ok')
        time_keeper = Thread(target=self._img_parts_time_keeper)
        time_keeper.start()
        print(self.img_parts)

    def _img_parts_time_keeper(self):
        delete_list = []
        for id_ in self.img_parts:
            if time.time() - self.img_parts[id_][TIME] > 30:
                delete_list.append(id_)
        tmp_dict = copy.deepcopy(self.img_parts)
        for i in delete_list:
            del tmp_dict[i]
        self.img_parts = tmp_dict

    # TODO заончить прототип
    def img_parts_handle(self):
        id_ = self.message.dict_message[IMG_ID]
        if id_ in self.img_parts:
            if self.img_parts[id_][IMG_SEQ] + 1 == self.message.dict_message[IMG_SEQ]\
                    and self.img_parts[id_][IMG_PCS] >= self.message.dict_message[IMG_SEQ]:
                self.img_parts[id_][IMG_SEQ] += 1
                self.img_parts[id_][IMG_DATA].append(self.message.dict_message[IMG_DATA])
            else:
                print("Части изображения не последовательны или количество элементов больше заданного количества")
        else:
            print('id {} нет в системе')
        # self.message.response_message_create(self.sock, OK, False)
        if self.img_parts[id_][IMG_SEQ] == self.img_parts[id_][IMG_PCS]:
            self._build_whole_message(id_)

    def _build_whole_message(self, id_):
        self.whole_received_img = {USER_ID: self.img_parts[id_][USER_ID], IMG: ''.join(self.img_parts[id_][IMG_DATA])}
        print(self.whole_received_img)

    def _img_announce_send(self, img_len, contact_name):
        self.message.create_img_message(img_len, contact_name)
        id_ = self.message.dict_message[IMG_ID]
        self.message.send_rcv_message(self.sock)
        return id_

    def _img_part_send(self, img_id, img_base64='', seq=1):
        self.message.create_img_parts_message(data=img_base64, seq=seq, id_=img_id)
        # self.message.send_rcv_message(self.sock)
        self.message.send_message(self.sock)

    @staticmethod
    def _split_img(img_base64='', img_len=0):
        return [img_base64[i:i+500] for i in range(0, img_len, 500)]

    def img_send(self, img_base64='', contact_name='test'):
        img_len = len(img_base64)
        id_ = self._img_announce_send(img_len, contact_name)
        splitted_img = self._split_img(img_base64, img_len)
        for seq, part in enumerate(splitted_img):
            self._img_part_send(id_, part, seq+1)
