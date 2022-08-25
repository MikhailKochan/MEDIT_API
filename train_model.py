from config import Config

from detectron2.config import get_cfg
from detectron2.data import MetadataCatalog, DatasetCatalog
from detectron2.data.datasets import register_coco_instances, register_pascal_voc
from detectron2.engine import DefaultPredictor, DefaultTrainer
from detectron2.utils.visualizer import ColorMode, Visualizer


