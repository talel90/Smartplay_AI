# Padel Analytics
![padel analytics](https://github.com/user-attachments/assets/f66e6141-6ad7-48ca-b363-f539af0782ca)

This repository applies computer vision techniques to extract valuable insights from a padel game recording like:
- Position and velocity of each player;
- Position and velocity of the ball;
- 2D game projection;
- Heatmaps;
- Ball velocity associated with distinct strokes;
- Player error rate.

To do so, several computer vision models where trained in order to:
1. Track the position of each individual players;
2. Players pose estimation with 13 degrees of freedom;
3. Players pose classification (e.g. backhand/forehand volley, bandeja, topspin smash, etc);
4. Predict ball hits.

The goal of this project is to provide precise and robust analytics using only a padel game recording. This implementation can be used to:
1. Upgrade live broadcasts providing interesting data to be shared with the audience or to be stored in a database for future analysis;
2. Generate precious insights to be used by padel coachs or players to enhance their path of continuous improvement.

# Setup
#### 1. Clone this repository.
#### 2. Setup virtual environment.
```
conda create -n python=3.12 padel_analytics pip
conda activate padel_analytics
pip install -r requirements.txt
```
#### 3. Install pytorch <https://pytorch.org/get-started/locally/>.
#### 4. Download weights.
   The current model weights used are available here https://drive.google.com/drive/folders/15tYyJL-Ifj50QKWMUsnsbZljZryU6xi8?fbclid=IwY2xjawGhPe9leHRuA2FlbQIxMAABHeeJigkPVRWK3bV63--zbAVg6xjZP3eitpx1Bl6kMsv7Pvil151e1s40ew_aem_CvV23ThCny6tURqh8MQqKQ   . Configure the config.py file with your own model checkpoints paths. 
# Inference
At the root of this repo, edit the file config.py accordingly and run:
````
python main.py
````

Legacy monolithic entrypoint (reference): `python old_main.py`.

#### REST API & React UI (SmartPlay AI)
Backend FastAPI (upload vidéo, suivi de job, résultats JSON) :

````
pip install -r requirements.txt
uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
````

Interface React dans `padel-ui/` :

````
cd padel-ui
npm install
npm run dev
````

**Phase 1 :** fournir les keypoints soit via ce formulaire / fichier `.json`, soit une fois sur le serveur dans `cache/fixed_keypoints_detection.json`. Voir `padel-ui/README.md` pour `VITE_API_URL` et `FRONTEND_ORIGINS`.

#### VRAM requirements
Using the default batch sizes one will need to have at least 8GB of VRAM. Reduce batch sizes editing the config.py file according to your needs. 
#### Implementation details
Currently this implementation assumes a fixed camera setup. `python main.py` runs `manual_keypoints_selection.py` logic first: if `cache/fixed_keypoints_detection.json` is missing, an OpenCV window lets you click **12** court keypoints on the first frame; otherwise the file is reused. You can run `python manual_keypoints_selection.py --force` only to redefine keypoints. See also `old_main.py` for the legacy all-in-one script. A video describing keypoints selection is available at `./examples/videos/select_keypoints.mp4`; the diagram order matches the comment at the top of `main.py`.
#### Keypoints selection
![select_keypoints_animation](https://github.com/user-attachments/assets/3c15131f-9943-477b-adeb-782cc32e8946)
#### Inference results
![inference](https://github.com/user-attachments/assets/85900918-683c-40b5-9faf-8e45f4c366e2
)
