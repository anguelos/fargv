"""
Tier-3 specification tests — user-mandated.
These define invariants and known-correct behaviours that must never regress.

AGENT RULE: Do NOT add, remove, or modify any test in this file without
explicit written approval from the user in the current conversation.
"""
import pytest
import fargv


def test_init_config_does_not_persist_stale_positional_default():
    """init_config_if_missing must not allow a stale config to override a
    subsequently changed FargvPositional coded default.
    Added: 2026-04-10, initiated by: Anguelos, reported by: nprenet.
    Regression: config written on first run with FargvPositional([]) persisted
    as [] and overrode a later coded default of ['b','a'] on subsequent runs.
    """
    import tempfile, os
    from fargv.parameters import FargvPositional

    cfg = tempfile.mktemp(suffix='.json')
    opts = dict(given_parameters=['prog', f'--config={cfg}'],
                auto_define_verbosity=False, auto_define_bash_autocomplete=False,
                auto_define_help=False, auto_define_user_interface=False)
    try:
        # Without config the coded default is always returned — no bug
        ns, _ = fargv.parse({'items': FargvPositional(['b', 'a'])},
                             given_parameters=['prog'], auto_define_config=False,
                             auto_define_verbosity=False, auto_define_bash_autocomplete=False,
                             auto_define_help=False, auto_define_user_interface=False)
        assert ns.items == ['b', 'a']

        # Run 1 with config: empty default — config is created with items: []
        fargv.parse({'items': FargvPositional([])}, **opts)

        # Run 2 with config: default changed — stale config must not win
        ns, _ = fargv.parse({'items': FargvPositional(['b', 'a'])}, **opts)
        assert ns.items == ['b', 'a']
    finally:
        if os.path.exists(cfg):
            os.unlink(cfg)
