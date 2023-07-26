from lightglue import LightGlue, SuperPoint, DISK, viz2d
from lightglue.utils import load_image, rbd
import argparse
import numpy as np
import gradio as gr
import torch
import logging

# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# parser = argparse.ArgumentParser()
# parser.add_argument('--img0', required=True)
# parser.add_argument('--img1', required=True)
# parser.add_argument('--out_path', required=True)

# args = parser.parse_args()


def numpy_image_to_torch(image: np.ndarray) -> torch.Tensor:
    """Normalize the image tensor and reorder the dimensions."""
    if image.ndim == 3:
        image = image.transpose((2, 0, 1))  # HxWxC to CxHxW
    elif image.ndim == 2:
        image = image[None]  # add channel axis
    else:
        raise ValueError(f'Not an image: {image.shape}')
    return torch.tensor(image / 255., dtype=torch.float)


class LightGlueWrapper(object):

    def __init__(self) -> None:
        # SuperPoint+LightGlue
        self.extractor = SuperPoint(max_num_keypoints=2048).eval().cuda()  # load the extractor
        self.matcher = LightGlue(features='superpoint').eval().cuda()  # load the matcher

        # logging.basicConfig(level=logging.DEBUG)

        # or DISK+LightGlue
        # extractor = DISK(max_num_keypoints=2048).eval().cuda()  # load the extractor
        # matcher = LightGlue(features='disk').eval().cuda()  # load the matcher

    @staticmethod
    def load(pil_image):
        pil_image = pil_image.convert('RGB')
        # convert to BGR format
        image = np.array(pil_image)
        # image = image[..., ::-1]
        return numpy_image_to_torch(image)

    def predict(self, image0, image1):
        # logger = logging.getLogger('predict')
        # logger.debug(f"image0: {image0}")
        # logger.debug(f"image1: {image1}")
        with torch.no_grad():
            image0 = self.load(image0).cuda()
            image1 = self.load(image1).cuda()

            # extract local features
            feats0 = self.extractor.extract(image0)  # auto-resize the image, disable with resize=None
            feats1 = self.extractor.extract(image1)

            # match the features
            matches01 = self.matcher({'image0': feats0, 'image1': feats1})
            
        feats0, feats1, matches01 = [rbd(x) for x in [feats0, feats1, matches01]]  # remove batch dimension
        matches = matches01['matches']  # indices with shape (K,2)
        # points0 = feats0['keypoints'][matches[..., 0]]  # coordinates in image #0, shape (K,2)
        # points1 = feats1['keypoints'][matches[..., 1]]  # coordinates in image #1, shape (K,2)

        kpts0, kpts1, matches = feats0['keypoints'], feats1['keypoints'], matches01['matches']
        m_kpts0, m_kpts1 = kpts0[matches[..., 0]], kpts1[matches[..., 1]]
        # axes = viz2d.plot_images([image0, image1])
        # viz2d.plot_matches(m_kpts0, m_kpts1, color='lime', lw=0.2)
        # viz2d.add_text(0, f'Stop after {matches01["stop"]} layers' + '\nMatches: {}'.format(len(m_kpts0)) + '\nConf: {}'.format(matches01['scores'].mean()), fs=10)

        # # kpc0, kpc1 = viz2d.cm_prune(matches01['prune0']), viz2d.cm_prune(matches01['prune1'])
        # # viz2d.plot_images([image0, image1])
        # # viz2d.plot_keypoints([kpts0, kpts1], colors=[kpc0, kpc1], ps=10)
        # viz2d.save_plot('temp2.png')

        # thresh = 100

        torch.cuda.empty_cache()
        return len(m_kpts0)


light_glue_wraper = LightGlueWrapper()

# ======== input =========
image_input_1 = gr.Image(type="pil", label='Image1')
image_input_2 = gr.Image(type="pil", label='Image2')

text_output = gr.Textbox(label="Output text")

gr.Interface(
    description="Feature matching.",
    fn=light_glue_wraper.predict,
    inputs=[image_input_1, image_input_2],
    outputs=[text_output]
).launch(share=True, enable_queue=True, server_port=22411)