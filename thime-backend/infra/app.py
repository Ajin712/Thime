#!/usr/bin/env python3
import aws_cdk as cdk
from thime_stack import ThimeStack

app = cdk.App()

ThimeStack(
    app,
    "ThimeStack",
    env=cdk.Environment(
        # aws configure에서 설정한 계정/리전 자동 사용
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region") or "ap-northeast-2",
    ),
)

app.synth()
