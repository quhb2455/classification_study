from utils import save_config, load_img, label_enc
import torch
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Dataset
from datetime import datetime
from glob import glob
import os
import cv2
import json

class SigmoidCustomDataset(Dataset):
    def __init__(self, imgs, sig_label, transform=None):
        self.imgs = imgs
        self.labels = sig_label
        # self.label_enc = label_enc(sorted(set(labels))) if labels != None else None
        self.transform = transform
        # self.binary_mode = binary_mode
        
    def __len__(self):
        return len(self.imgs)

    def __getitem__(self, index):
        img_path = self.imgs[index]
        
        image = load_img(img_path)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        if self.transform :
            image = self.transform(image=image)['image']

        if self.labels is not None:
            # if self.binary_mode :
            #     label = torch.tensor(self.binary_encoder(self.label_enc[self.labels[index]]), dtype=torch.long)
            # else :
            #     label = self.label_enc[self.labels[index]]
            label = torch.tensor(self.labels[index])
            return image, label

        else:
            return image

class MultiHeadCustomDataset(Dataset):
    def __init__(self, imgs, labels, transform=None, senario=1):
        self.imgs = imgs
        self.labels = labels
        self.label_enc = label_enc(sorted(set(labels))) if labels != None else None
        self.transform = transform
        self.senario = senario
        
        self.first_group = {"곰팡이":0, "녹오염":0, "오염":0, "반점":0, 
                            "가구수정":1, "걸레받이수정":1, "몰딩수정":1, "석고수정":1, "창틀,문틀수정":1, 
                            "꼬임":2, "들뜸":2, "울음":2, "면불량":2, "터짐":2, 
                            "틈새과다":3, "이음부불량":3, 
                            "오타공":4, "피스":4, 
                            "훼손":5}
        self.second_group = [{"곰팡이":0, "녹오염":1, "오염":2, "반점":3}, 
                            {"가구수정":0, "걸레받이수정":1, "몰딩수정":2, "석고수정":3, "창틀,문틀수정":4},
                            {"꼬임":0, "들뜸":1, "울음":2, "면불량":3, "터짐":4},
                            {"틈새과다":0, "이음부불량":1},
                            {"오타공":0, "피스":1},
                            {"훼손":0}]
        
    def __len__(self):
        return len(self.imgs)

    def __getitem__(self, index):
        img_path = self.imgs[index]
        
        image = load_img(img_path)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        if self.transform :
            image = self.transform(image=image)['image']

        if self.labels is not None:
            label_name = self.labels[index]
            # label = self.label_enc[label_name]
            label = torch.tensor(self.binary_encoder(self.label_enc[label_name]), dtype=torch.long)

            first_grouping = self.first_group[label_name]
            second_grouping = self.second_group[first_grouping][label_name]
            
            second_mask = [0 for i in range(len(self.first_group))]
            total_len = sum([len(self.second_group[i]) for i in range(first_grouping)])
            

            
            if self.senario == 1 :     
                second_mask[total_len : total_len + len(self.second_group[first_grouping])] = [1 if i == second_grouping else 0 for i in range(len(self.second_group[first_grouping]))]
            elif self.senario == 2 :
                second_mask[total_len : total_len + len(self.second_group[first_grouping])] = [1 for i in range(len(self.second_group[first_grouping]))]

            return image, label, first_grouping, torch.tensor(second_mask, dtype=torch.bool)

        else:
            return image
    
    def binary_encoder(self, label):
        total_label_len = len(self.label_enc.keys())
        return [1 if i == label else 0 for i in range(total_label_len) ]
    

class CustomDataset(Dataset):
    def __init__(self, imgs, labels, transform=None, binary_mode=False):
        self.imgs = imgs
        self.labels = labels
        self.label_enc = label_enc(sorted(set(labels))) if labels != None else None
        self.transform = transform
        self.binary_mode = binary_mode
        
    def __len__(self):
        return len(self.imgs)

    def __getitem__(self, index):
        img_path = self.imgs[index]
        
        image = load_img(img_path)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        if self.transform :
            image = self.transform(image=image)['image']

        if self.labels is not None:
            if self.binary_mode :
                label = torch.tensor(self.binary_encoder(self.label_enc[self.labels[index]]), dtype=torch.long)
            else :
                label = self.label_enc[self.labels[index]]
            
            return image, label

        else:
            return image
    
    def binary_encoder(self, label):
        total_label_len = len(self.label_enc.keys())
        return [1 if i == label else 0 for i in range(total_label_len) ]
    
class DatasetCreater() :
    def __init__(self) -> None:
        self.label_dec = {idx:n for idx, n in enumerate(self.label_name)}
        self.label_enc = {n:idx for idx, n in enumerate(self.label_name)}
        
    
    def create_dataset(self, transform, **cfg) :
        img_path, label_list = self.get_data(**cfg)        
        
        if cfg["mode"] == "train" :
            save_config(transform[0].to_dict(), cfg["save_path"], save_name="train_transform")
            save_config(transform[1].to_dict(), cfg["save_path"], save_name="valid_transform")
            
            return [CustomDataset(img_path[0], label_list[0], transform=transform[0], binary_mode=cfg["binary_mode"]), 
                    CustomDataset(img_path[1], label_list[1], transform=transform[1], binary_mode=cfg["binary_mode"])]
            
        elif cfg["mode"] == 'infer' :
            save_config(transform.to_dict(), cfg["output_path"], save_name="infer_transform")
            return CustomDataset(img_path, label_list, transform=transform)
    
    
    def create_dataloader(self, transform, **cfg) :
        ds = self.create_dataset(transform, **cfg)
        
        if isinstance(ds, list) :
            return (DataLoader(ds[0], batch_size=cfg["batch_size"], shuffle=cfg["shuffle"], num_workers=cfg["num_worker"]), 
                    DataLoader(ds[1], batch_size=cfg["batch_size"], shuffle=cfg["shuffle"], num_workers=cfg["num_worker"]))
        else :
            return DataLoader(ds, batch_size=cfg["batch_size"], shuffle=cfg["shuffle"], num_workers=cfg["num_worker"])
        
        
    def get_data(self, **cfg) :
        data_path = cfg["data_path"]
        mode = cfg["mode"]
        
        img_path_list = []
        label_list = []
        
        if mode == "infer" :
            for p in glob(os.path.join(data_path, "*")) :
                img_path_list.append(p)
            return img_path_list, None
        
        else :
            for p in glob(os.path.join(data_path, "*", "*")) :
                img_path_list.append(p)
                label_list.append(p.split("\\")[-2])
            train_img, valid_img, train_label, valid_label = train_test_split(img_path_list, 
                                                                              label_list, 
                                                                              test_size=0.2, 
                                                                              stratify=label_list, 
                                                                              random_state=2455)
            return [train_img, valid_img], [train_label, valid_label]
    
