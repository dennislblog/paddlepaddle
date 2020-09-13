from parl import Agent, layers
import paddle.fluid as fluid
import numpy as np


class Agent(Agent):
    def __init__(self, algorithm, obs_dim, act_dim):
        self.obs_dim = obs_dim
        self.act_dim = act_dim
        super(Agent, self).__init__(algorithm)
        self.alg.sync_target(decay=0)


    def build_program(self):
        self.pred_program = fluid.Program()
        self.learn_program = fluid.Program()

        with fluid.program_guard(self.pred_program):  # 搭建计算图用于 预测动作，定义输入输出变量
            obs = layers.data(name='obs', shape=[self.obs_dim], dtype='float32')
            self.act_mean = self.alg.predict(obs)

        with fluid.program_guard(self.learn_program):  
            # 搭建计算图用于 更新policy网络，定义输入输出变量
            obs = layers.data( name='obs', shape=[self.obs_dim], dtype='float32')
            act = layers.data(name='act', shape=[self.act_dim], dtype='float32') 
            reward = layers.data(name='reward', shape=[], dtype='float32')
            next_obs = layers.data(name='next_obs', shape=[self.obs_dim], dtype='float32')
            terminal = layers.data(name='terminal', shape=[], dtype='bool')
            self.cost = self.alg.learn(obs, act, reward, next_obs, terminal)

    def sample(self, obs):
        obs = np.expand_dims(obs, axis=0)  # 增加一维维度
        act_prob = self.fluid_executor.run(
            self.pred_program,
            feed={'obs': obs.astype('float32')},
            fetch_list=[self.act_prob])[0]
        act_prob = np.squeeze(act_prob, axis=0)  # 减少一维维度
        act = np.random.choice(range(self.act_dim), p=act_prob)  # 根据动作概率选取动作
        return act

    def predict(self, obs):
        obs = np.expand_dims(obs, axis=0)
        act_mean = self.fluid_executor.run(
            self.pred_program,
            feed={'obs': obs.astype('float32')},
            fetch_list=[self.act_mean])[0]
        # act_prob = np.squeeze(act_prob, axis=0)
        # act = np.argmax(act_prob)  # 根据动作概率选择概率最高的动作
        return act_mean

    def learn(self, obs, act, reward, next_obs, terminal):
        # act = np.expand_dims(act, axis=-1)
        feed = {
            'obs': obs.astype('float32'),
            'act': act.astype('float32'),
            'reward': reward.astype('float32'),
            'next_obs': next_obs.astype('float32'),
            'terminal': terminal.astype('bool')
        }
        [a_cost, c_cost] = self.fluid_executor.run(
            self.learn_program, feed=feed, fetch_list=self.cost)
        self.alg.sync_target()
        return a_cost, c_cost