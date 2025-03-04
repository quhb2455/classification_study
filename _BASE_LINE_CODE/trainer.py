from utils import score, logging

import torch
import numpy as np
import os
from tqdm import tqdm
import time

class Trainer() :
    def __init__(self) -> None:
        # self.train_loader = None
        # self.valid_loader = None
        # self.criterion = None
        # self.optimizer = None
        # self.model = None
        
        self.best_score = 0
        self.early_stop_cnt = 0
        
    def run(self, **cfg) :
        self.log = logging(os.path.join(cfg["log_path"], cfg["model_name"], time.strftime('%Y%m%d_%H_%M_%S', time.localtime())))
        
        start_epoch = self.train_weight_load(cfg["weight_path"]) if cfg["reuse"] else 0
            
        for e in range(start_epoch, cfg["epochs"]) :
            self.train_on_epoch(e, **cfg)
            valid_acc, valid_loss = self.valid_on_epoch(e, **cfg)
            
            self.logging({"Valid ACC" : valid_acc, "Valid Loss" : valid_loss}, e)
            self.save_checkpoint(e, valid_acc, **cfg)
            
            if self.early_stop_cnt == cfg["early_stop_patient"] :
                print("=== EARLY STOP ===")
                break
    
    def train_weight_load(self, weight_path) :
        checkpoint = torch.load(weight_path)
        self.model.load_state_dict(checkpoint['model_state_dict'])        
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        return checkpoint['epoch'] + 1
        
    def train_on_epoch(self, epoch, **cfg):
        self.model.train()
        train_acc, train_loss = [], []
        tqdm_train = tqdm(self.train_loader)
        for step, (img, label) in enumerate(tqdm_train) :
            batch_res = self.train_on_batch(img, label, **cfg)
            
            train_acc.append(batch_res["acc"])
            train_loss.append(batch_res["loss"])
            
            log = {
                "Epoch" : epoch,
                "Training Acc" : np.mean(train_acc),
                "Training Loss" : np.mean(train_loss),
            }
            tqdm_train.set_postfix(log)
            self.logging(log, step)
            
        # self.scheduler.step()
        
    def train_on_batch(self, img, label, **cfg) :
        self.optimizer.zero_grad()

        img = img.to(cfg["device"])
        label = label.to(cfg["device"])
        
        output = self.model(img)
        loss = self.criterion(output, label)
        
        loss.backward()
        self.optimizer.step()
        
        acc = score(label, output)
        
        batch_metric = {
            "acc" : acc,
            "loss" : loss.item()
        }
        return batch_metric 
    
    def valid_on_epoch(self, epoch, **cfg):
        self.model.eval()
        valid_acc, valid_loss = [], []
        tqdm_valid = tqdm(self.valid_loader)
        for step, (img, label) in enumerate(tqdm_valid) :
            batch_res = self.valid_on_batch(img, label, **cfg)
            
            valid_acc.append(batch_res["acc"])
            valid_loss.append(batch_res["loss"])
            log = {
                "Epoch" : epoch,
                "Validation Acc" : np.mean(valid_acc),
                "Validation Loss" : np.mean(valid_loss),
            }
            tqdm_valid.set_postfix(log)
            
        return np.mean(valid_acc), np.mean(valid_loss)
    
    def valid_on_batch(self, img, label, **cfg):
        img = img.to(cfg["device"])
        label = label.to(cfg["device"])
        
        output = self.model(img)
        loss = self.criterion(output, label)
        
        acc = score(label, output)
        
        batch_metric = {
            "acc" : acc,
            "loss" : loss.item()
        }
        
        return batch_metric
    
    def save_checkpoint(self, epoch, val_acc, **cfg) :
        if self.best_score < val_acc:
            self.best_score = val_acc
            torch.save({
                "epoch": epoch,
                "model_state_dict": self.model.state_dict(),
                "optimizer_state_dict": self.optimizer.state_dict()
            }, os.path.join(cfg["save_path"], str(epoch) + 'E-val' + str(self.best_score) + '-' + cfg["model_name"] + '.pth'))
            self.early_stop_cnt = 0 
        else : 
            self.early_stop_cnt += 1
            
    def logging(self, log_dict, step) :
        for k, v in log_dict.items():
            if k == "Epoch" : continue
            self.log.add_scalar(k, v, step)