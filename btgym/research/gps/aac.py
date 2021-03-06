import tensorflow as tf

from btgym.algorithms import BaseAAC
from .loss import guided_aac_loss_def_0_0, guided_aac_loss_def_0_1, guided_aac_loss_def_0_3
from btgym.research.verbose_env_runner import VerboseEnvRunnerFn


class GuidedAAC(BaseAAC):
    """
    Actor-critic framework augmented with expert actions imitation loss:
    L_gps = aac_lambda * L_a3c + guided_lambda * L_im.

    This implementation is loosely refereed as 'guided policy search' after algorithm described in paper
    by S. Levine and P. Abbeel `Learning Neural Network Policies with Guided PolicySearch under Unknown Dynamics`

    in a sense that exploits idea of fitting 'local' (here - single episode) oracle for environment with
    generally unknown dynamics and use actions demonstrated by it to optimize trajectory distribution for training agent.

    Note that this particular implementation of expert does not provides
    complete action-state space trajectory for agent to follow.
    Instead it estimates `advised` categorical distribution over actions conditioned on `external` (i.e. price dynamics)
    state observations only.

    Papers:
        - Levine et al., 'Learning Neural Network Policies with Guided PolicySearch under Unknown Dynamics'
            https://people.eecs.berkeley.edu/~svlevine/papers/mfcgps.pdf

        - Brys et al., 'Reinforcement Learning from Demonstration through Shaping'
            https://www.ijcai.org/Proceedings/15/Papers/472.pdf

        - Wiewiora et al., 'Principled Methods for Advising Reinforcement Learning Agents'
            http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.14.6412&rep=rep1&type=pdf

    """
    def __init__(
            self,
            expert_loss=guided_aac_loss_def_0_3,
            aac_lambda=1.0,
            guided_lambda=1.0,
            runner_fn_ref=VerboseEnvRunnerFn,
            _aux_render_modes=('action_prob', 'value_fn', 'lstm_1_h', 'lstm_2_h'),
            name='GuidedA3C',
            **kwargs
    ):
        """

        Args:
            expert_loss:        callable returning tensor holding on_policy imitation loss graph and summaries
            aac_lambda:         float, main on_policy a3c loss lambda
            guided_lambda:      float, imitation loss lambda
            name:               str, name scope
            **kwargs:           see BaseAAC kwargs
        """
        try:
            self.expert_loss = expert_loss
            self.aac_lambda = aac_lambda
            self.guided_lambda = guided_lambda

            super(GuidedAAC, self).__init__(
                runner_fn_ref=runner_fn_ref,
                _aux_render_modes=_aux_render_modes,
                name=name,
                **kwargs
            )

        except:
            msg = 'GuidedAAC.__init()__ exception occurred' + \
                  '\n\nPress `Ctrl-C` or jupyter:[Kernel]->[Interrupt] for clean exit.\n'
            self.log.exception(msg)
            raise RuntimeError(msg)

    def _make_loss(self):
        """
        Augments base loss with expert actions imitation loss

        Returns:
            tensor holding estimated loss graph
            list of related summaries
        """
        aac_loss, summaries = self._make_base_loss()

        guided_loss, guided_summary = self.expert_loss(
            pi_actions=self.local_network.on_logits,
            expert_actions=self.local_network.expert_actions,
            name='on_policy',
            verbose=True
        )
        loss = self.aac_lambda * aac_loss + self.guided_lambda * guided_loss
        summaries += guided_summary

        self.log.notice('aac_lambda: {:1.6f}, guided_lambda: {:1.6f}'.format(self.aac_lambda, self.guided_lambda))

        return loss, summaries

