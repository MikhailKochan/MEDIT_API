import glob
import time
import os
from flask import current_app
from app import db, models
from app.models import Images, Predict
import torch
import cv2
from tqdm import tqdm, trange
from pascal_voc_writer import Writer
from config import basedir


def watcher():
    while True:
        files = glob.glob(current_app.config['UPLOAD_FOLDER'] + '/*')
        query = Images.query.all()
        old_img = [el.filename for el in query]
        for new in files:
            if os.path.basename(new) not in old_img:
                db.session.add(Images(new))
                current_app.logger.info(f"{os.path.basename(new)} add in DB")
        # need_cut = [_ for _ in query if _.cut_file is False]
        # for el in need_cut:
        #     print(f"{el} need cut")
        db.session.commit()
        break
        # time.sleep(app.config['UPDATE_TIME'])

# cfg, mitoz_metadata = create_config(register_pascal_voc, MetadataCatalog, get_cfg)
# predictor = load_model(cfg, DefaultPredictor)

    # if not os.getcwd() == app.config['DETECTRON']:
    #     os.chdir(app.config['DETECTRON'])
    # from detectron2.config import get_cfg
    # from detectron2.data import MetadataCatalog, DatasetCatalog
    # from detectron2.data.datasets import register_coco_instances, register_pascal_voc
    # # import some common detectron2 utilities
    # from detectron2.engine import DefaultPredictor, DefaultTrainer


# class medit(object):
#     pass


class medit(object):
    @classmethod
    def pr(cls):
        print(current_app.config['CLASS_NAMES'])
        print('it is work')

    def create_config(self, register_pascal_voc, MetadataCatalog, get_cfg):
        try:
            register_pascal_voc("mitoze_train", "E:/mitosplus2", "train", "2012", current_app.config['CLASS_NAMES'])
            mitoz_metadata = MetadataCatalog.get("mitoze_train")

            mitoz_metadata.thing_colors = [(0, 0, 0), (1.0, 0, 0), (1.0, 1.0, 240.0 / 255)]
            torch.multiprocessing.freeze_support()

            print('loop')

            num_gpu = 1
            bs = (num_gpu * 2)
            cfg = get_cfg()
            cfg.merge_from_file("./configs/PascalVOC-Detection/faster_rcnn_R_50_FPN.yaml")
            cfg.DATASETS.TRAIN = ("mitoze_train",)
            cfg.DATASETS.TEST = ()  # no metrics implemented for this dataset
            cfg.DATALOADER.NUM_WORKERS = 2
            cfg.MODEL.WEIGHTS = "detectron2://ImageNetPretrained/MSRA/R-50.pkl"  # initialize from model zoo
            cfg.SOLVER.IMS_PER_BATCH = 4
            cfg.SOLVER.BASE_LR = 0.02 * bs / 16
            cfg.SOLVER.MAX_ITER = 4000  # 300 iterations seems good enough, but you can certainly train longer
            cfg.MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE = 256  # faster, and good enough for this toy dataset
            cfg.MODEL.ROI_HEADS.NUM_CLASSES = 4  # 3 classes (data, fig, hazelnut)
            # cfg.OUTPUT_DIR = app.config['']
            os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
            cfg.MODEL.DEVICE = current_app.config['_CUDA_SET']
            return cfg, mitoz_metadata
        except Exception as e:
            print(f'ERROR in create config: {e}')

    def load_model(self, cfg, DefaultPredictor):
        cfg.MODEL.WEIGHTS = os.path.join(cfg.OUTPUT_DIR, "model_final.pth")
        cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.5  # set the testing threshold for this model
        predictor = DefaultPredictor(cfg)
        return predictor

    def make_predict(self, image):
        try:
            os.chdir(current_app.config['DETECTRON'])

            from detectron2.config import get_cfg
            from detectron2.data import MetadataCatalog, DatasetCatalog
            from detectron2.data.datasets import register_coco_instances, register_pascal_voc
            # import some common detectron2 utilities
            from detectron2.engine import DefaultPredictor, DefaultTrainer
            from detectron2.utils.visualizer import ColorMode
            from detectron2.utils.visualizer import Visualizer

            cfg, mitoz_metadata = create_config(register_pascal_voc, MetadataCatalog, get_cfg)
            predictor = load_model(cfg, DefaultPredictor)

            all_mitoz = 0
            max_mitoz_in_one_img = 0

            path_img = glob.glob(f"{current_app.config['CUTTING_FOLDER']}/{image.filename}/*.jpg")

            if len(path_img) < 1:
                image.cutting()
                path_img = glob.glob(f"{current_app.config['CUTTING_FOLDER']}/{image.filename}/*")
                if len(path_img) < 1:
                    return f"{image.filename} have problem with cutting"

            total = len(path_img)
            path_to_save = f"{current_app.config['DRAW']}/{image.filename}"
            print(total)
            # percent = 49
            # redis_cache.set(image.dtime, percent)

            if not os.path.exists(path_to_save):
                os.mkdir(path_to_save)
                print(f"Directory {image.filename} for draw created")
            with tqdm(total=total, position=0, leave=False) as pbar:
                for img in path_img:
                    pbar.set_description(f"Total img: {total}. Start create predict:")

                    filename = os.path.basename(img)[:-4]
                    path_to_save_xml = os.path.dirname(img)
                    # print("path_to_save_xml", path_to_save_xml)
                    # print('file name:', filename)
                    im = cv2.imread(img)
                    outputs = predictor(im)

                    outputs = outputs["instances"].to("cpu")

                    classes = outputs.pred_classes.tolist() if outputs.has("pred_classes") else None
                    boxes = outputs.pred_boxes if outputs.has("pred_boxes") else None

                    mitoz = current_app.config["CLASS_NAMES"].index('mitoz')

                    if mitoz in classes:
                        v = Visualizer(im[:, :, ::-1],
                                       metadata=mitoz_metadata,
                                       scale=1,
                                       instance_mode=ColorMode.SEGMENTATION)

                        v = v.draw_instance_predictions(outputs)
                        cv2.imwrite(os.path.join(path_to_save, f"{filename}.jpg"), v.get_image()[:, :, ::-1])

                        all_mitoz += classes.count(mitoz)
                        if classes.count(mitoz) > max_mitoz_in_one_img:
                            max_mitoz_in_one_img = classes.count(mitoz)
                            img_name = f"{filename}.jpg"
                        # print(f"al mitoz in {filename}:", all_mitoz)

                    boxes = boxes.tensor.detach().numpy()
                    num_instances = len(boxes)

                    height, width = im.shape[:2]
                    writer = Writer(img, height, width)
                    for i in range(num_instances):
                        x0, y0, x1, y1 = boxes[i]
                        x0 += 1.0
                        y0 += 1.0
                        writer.addObject(current_app.config["CLASS_NAMES"][classes[i]], int(x0), int(y0), int(x1), int(y1))
                    writer.save(f'{path_to_save_xml}/{filename}.xml')

                    # percent += 1/total*49
                    # redis_cache.set(image.dtime, int(percent))

                    pbar.update(1)

            # create_zip(image.filename, image.dtime)
            # create_zip(image.filename, image.dtime, "draw")
            data = Predict(
                status="Done",
                result_all_mitoz=all_mitoz,
                result_max_mitoz_in_one_img=max_mitoz_in_one_img,
                count_img=total,
                name_img_have_max_mitoz=img_name,
                model=cfg.MODEL.WEIGHTS,
                image_id=image.id
            )
            db.session.add(data)
            db.session.commit()
            # percent = 99
            # redis_cache.set(image.dtime, f"{percent},{all_mitoz}")
            os.chdir(basedir)
        except Exception as e:
            print(f"ERROR in predict: {e}")
            current_app.logger.error(e)
            os.chdir(basedir)


class Medit(object):
    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        if not hasattr(app, 'extensions'):  # pragma: no cover
            app.extensions = {}
        app.extensions['medit'] = medit
        app.context_processor(self.context_processor)

    @staticmethod
    def context_processor():
        return {
            'medit': current_app.extensions['medit']
        }
    #
    # def create(self):
    #     return current_app.extensions['medit']()


def imprt(app):
    if not os.getcwd() == app.config['DETECTRON']:
        os.chdir(app.config['DETECTRON'])

    from detectron2.config import get_cfg
    from detectron2.data import MetadataCatalog, DatasetCatalog
    from detectron2.data.datasets import register_coco_instances, register_pascal_voc
    from detectron2.data.datasets.coco import convert_to_coco_json, load_coco_json
    # import some common detectron2 utilities
    from detectron2.engine import DefaultPredictor, DefaultTrainer
    from detectron2.utils.logger import setup_logger
    from detectron2.utils.visualizer import ColorMode, Visualizer
    from pascal_voc_writer import Writer

    register_pascal_voc("mitoze_train", "E:/mitosplus2", "train", "2012", app.config['CLASS_NAMES'])
    mitoz_metadata = MetadataCatalog.get("mitoze_train")

    mitoz_metadata.thing_colors = app.config['_COLORS']
    torch.multiprocessing.freeze_support()

    print('loop')

    num_gpu = 1
    bs = (num_gpu * 2)
    cfg = get_cfg()
    cfg.merge_from_file("./configs/PascalVOC-Detection/faster_rcnn_R_50_FPN.yaml")
    cfg.DATASETS.TRAIN = ("mitoze_train",)
    cfg.DATASETS.TEST = ()  # no metrics implemented for this dataset
    cfg.DATALOADER.NUM_WORKERS = 2
    cfg.MODEL.WEIGHTS = "detectron2://ImageNetPretrained/MSRA/R-50.pkl"  # initialize from model zoo
    cfg.SOLVER.IMS_PER_BATCH = 4
    cfg.SOLVER.BASE_LR = 0.02 * bs / 16
    cfg.SOLVER.MAX_ITER = app.config['_ITER']  # 300 iterations seems good enough, but you can certainly train longer
    cfg.MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE = 256  # faster, and good enough for this toy dataset
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 4  # 3 classes (data, fig, hazelnut)
    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
    cfg.MODEL.DEVICE = app.config['_CUDA_SET']

    cfg.MODEL.WEIGHTS = os.path.join(cfg.OUTPUT_DIR, "model_final.pth")
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.5  # set the testing threshold for this model
    predictor = DefaultPredictor(cfg)
    if not hasattr(app, 'extensions'):  # pragma: no cover
        app.extensions = {}
    app.extensions['predictor'] = predictor
    app.extensions['Visualizer'] = Visualizer
    app.extensions['ColorMode'] = ColorMode
    os.chdir(app.config['BASEDIR'])
    return predictor
