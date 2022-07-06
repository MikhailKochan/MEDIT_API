import glob
import time
import os
from app import app, db, models
from app.models import Images


def watcher():
    while True:
        files = glob.glob(app.config['UPLOAD_FOLDER'] + '/*')
        query = Images.query.all()
        old_img = [el.filename for el in query]
        for new in files:
            if os.path.basename(new) not in old_img:
                db.session.add(Images(new))
                app.logger.info(f"{os.path.basename(new)} add in DB")
        need_cut = [_ for _ in query if _.cut_file is False]
        for el in need_cut:
            pass
        db.session.commit()
        break
        time.sleep(app.config['UPDATE_TIME'])


# def make_predictor(predictor, mitoz_metadata, image, CLASS_NAMES=CLASS_NAMES):
#     all_mitoz = 0
#     max_mitoz_in_one_img = 0
#     # path = f"./static/cutting_file/{dataset_folder}"
#
#     path_img = glob.glob(f"{image.path_to_save}/*.jp*g")
#     path_to_save = f"./static/draw/{image.filename}"
#
#     total = len(path_img)
#     percent = 49
#     redis_cache.set(image.dtime, percent)
#
#     if not os.path.exists(path_to_save):
#         os.mkdir(path_to_save)
#         print(f"Directory {image.filename} for draw created")
#     with tqdm(total=total, position=0, leave=False) as pbar:
#         for img in path_img:
#             pbar.set_description(f"Total img: {total}. Start create xml:")
#
#             filename = os.path.basename(img)[:-4]
#             path_to_save_xml = os.path.dirname(img)
#             # print("path_to_save_xml", path_to_save_xml)
#             # print('file name:', filename)
#             im = cv2.imread(img)
#             outputs = predictor(im)
#
#             outputs = outputs["instances"].to("cpu")
#
#             classes = outputs.pred_classes.tolist() if outputs.has("pred_classes") else None
#             boxes = outputs.pred_boxes if outputs.has("pred_boxes") else None
#
#             mitoz = CLASS_NAMES.index('mitoz')
#
#             if mitoz in classes:
#                 v = Visualizer(im[:, :, ::-1],
#                                metadata=mitoz_metadata,
#                                scale=1,
#                                instance_mode=ColorMode.SEGMENTATION)
#
#                 v = v.draw_instance_predictions(outputs)
#                 cv2.imwrite(os.path.join(path_to_save, f"{filename}.jpg"), v.get_image()[:, :, ::-1])
#
#                 all_mitoz += classes.count(mitoz)
#                 if classes.count(mitoz) > max_mitoz_in_one_img:
#                     max_mitoz_in_one_img = classes.count(mitoz)
#                     img_name = f"{filename}.jpg"
#                 # print(f"al mitoz in {filename}:", all_mitoz)
#
#             boxes = boxes.tensor.detach().numpy()
#             num_instances = len(boxes)
#
#             height, width = im.shape[:2]
#             writer = Writer(img, height, width)
#             for i in range(num_instances):
#                 x0, y0, x1, y1 = boxes[i]
#                 x0 += 1.0
#                 y0 += 1.0
#                 writer.addObject(CLASS_NAMES[classes[i]], int(x0), int(y0), int(x1), int(y1))
#             writer.save(f'{path_to_save_xml}/{filename}.xml')
#
#             percent += 1/total*49
#             redis_cache.set(image.dtime, int(percent))
#
#             pbar.update(1)
#     # #TODO make python log https://docs.python.org/3/howto/logging.html
#     # with open(os.path.join(path_to_save, f"{dataset_folder}_Log.txt"), 'a') as f:
#     #     f.writelines(f"{dtime} in {dataset_folder} have detected {all_mitoz} mitoz")
#     #     f.writelines('\n')
#     #     f.writelines(dict.fromkeys([dataset_folder], all_mitoz))
#     #     f.writelines('\n')
#     create_zip(image.filename, image.dtime)
#     create_zip(image.filename, image.dtime, "draw")
#     data = {
#         "id": image.id,
#         "status": "Done",
#         "result all mitoz": all_mitoz,
#         "result max mitoz in one img": max_mitoz_in_one_img,
#         "counts img": len(path_img),
#         "name img have max mitoz": img_name
#     }
#     update_bd(data, image.dtime)
#     percent = 99
#     redis_cache.set(image.dtime, f"{percent},{all_mitoz}")
