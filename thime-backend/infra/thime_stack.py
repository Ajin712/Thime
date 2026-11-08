from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_cognito as cognito,
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_iam as iam,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_events as events,
    aws_events_targets as targets,
    aws_sns as sns,
)
from constructs import Construct
import os


class ThimeStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ─────────────────────────────────────────
        # 1. Cognito User Pool
        # ─────────────────────────────────────────
        user_pool = cognito.UserPool(
            self,
            "ThimeUserPool",
            user_pool_name="thime-user-pool",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=False),
                nickname=cognito.StandardAttribute(required=False, mutable=True),
            ),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_digits=True,
                require_symbols=False,
                require_uppercase=False,
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.DESTROY,  # 해커톤: 스택 삭제 시 같이 삭제
        )

        # Cognito App Client (프론트엔드용)
        user_pool_client = cognito.UserPoolClient(
            self,
            "ThimeUserPoolClient",
            user_pool=user_pool,
            user_pool_client_name="thime-web-client",
            auth_flows=cognito.AuthFlow(
                user_srp=True,
                user_password=True,
            ),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(authorization_code_grant=True),
                scopes=[cognito.OAuthScope.OPENID, cognito.OAuthScope.EMAIL, cognito.OAuthScope.PROFILE],
            ),
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(30),
        )

        # Cognito Authorizer (API Gateway에서 사용)
        cognito_authorizer = apigw.CognitoUserPoolsAuthorizer(
            self,
            "ThimeCognitoAuthorizer",
            cognito_user_pools=[user_pool],
            authorizer_name="ThimeCognitoAuthorizer",
            identity_source="method.request.header.Authorization",
        )

        # ─────────────────────────────────────────
        # 2. DynamoDB 테이블
        # ─────────────────────────────────────────

        # users 테이블
        users_table = dynamodb.Table(
            self,
            "ThimeUsersTable",
            table_name="thime-users",
            partition_key=dynamodb.Attribute(name="userId", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # records 테이블
        records_table = dynamodb.Table(
            self,
            "ThimeRecordsTable",
            table_name="thime-records",
            partition_key=dynamodb.Attribute(name="userId", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="recordId", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )
        # 날짜 기반 재노출(F3)을 위한 GSI
        records_table.add_global_secondary_index(
            index_name="userId-createdAt-index",
            partition_key=dynamodb.Attribute(name="userId", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="createdAt", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # questions 테이블
        questions_table = dynamodb.Table(
            self,
            "ThimeQuestionsTable",
            table_name="thime-questions",
            partition_key=dynamodb.Attribute(name="date", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="questionId", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # feeds 테이블 (F5: 다른 생각 보기)
        feeds_table = dynamodb.Table(
            self,
            "ThimeFeedsTable",
            table_name="thime-feeds",
            partition_key=dynamodb.Attribute(name="questionId", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="userId", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # comments 테이블 (버블 메커니즘: 댓글 & 선택적 답장)
        # PK: feedId = "{questionId}#{answererUserId}"
        # SK: commentId = "{createdAt}#{commenterUserId}"
        comments_table = dynamodb.Table(
            self,
            "ThimeCommentsTable",
            table_name="thime-comments",
            partition_key=dynamodb.Attribute(name="feedId", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="commentId", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )
        # 댓글 작성자가 자신의 댓글 목록 조회용 GSI
        comments_table.add_global_secondary_index(
            index_name="commenterUserId-createdAt-index",
            partition_key=dynamodb.Attribute(name="commenterUserId", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="createdAt", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # ─────────────────────────────────────────
        # 3. S3 버킷 (음성 파일 저장)
        # ─────────────────────────────────────────
        audio_bucket = s3.Bucket(
            self,
            "ThimeAudioBucket",
            bucket_name=f"thime-audio-{self.account}",
            cors=[
                s3.CorsRule(
                    allowed_methods=[s3.HttpMethods.PUT, s3.HttpMethods.GET],
                    allowed_origins=["*"],  # 프로덕션에서는 도메인으로 제한
                    allowed_headers=["*"],
                )
            ],
            lifecycle_rules=[
                # 음성 파일은 30일 후 자동 삭제 (비용 절약)
                s3.LifecycleRule(expiration=Duration.days(30))
            ],
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # ─────────────────────────────────────────
        # 4. Lambda 공통 환경변수 & IAM Role
        # ─────────────────────────────────────────
        common_env = {
            "USERS_TABLE": users_table.table_name,
            "RECORDS_TABLE": records_table.table_name,
            "QUESTIONS_TABLE": questions_table.table_name,
            "FEEDS_TABLE": feeds_table.table_name,
            "COMMENTS_TABLE": comments_table.table_name,
            "AUDIO_BUCKET": audio_bucket.bucket_name,
            "USER_POOL_ID": user_pool.user_pool_id,
            "REGION": self.region,
        }

        lambda_role = iam.Role(
            self,
            "ThimeLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
            ],
        )
        # DynamoDB 접근 권한
        for table in [users_table, records_table, questions_table, feeds_table, comments_table]:
            table.grant_read_write_data(lambda_role)

        # S3 접근 권한
        audio_bucket.grant_read_write(lambda_role)

        # Transcribe 권한
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["transcribe:StartTranscriptionJob", "transcribe:GetTranscriptionJob"],
                resources=["*"],
            )
        )

        # Bedrock 권한 (Claude)
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                resources=["*"],
            )
        )

        # SNS 권한 (알림)
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["sns:Publish"],
                resources=["*"],
            )
        )

        # ─────────────────────────────────────────
        # 5. Lambda 함수들
        # ─────────────────────────────────────────
        lambda_base_path = os.path.join(os.path.dirname(__file__), "..", "lambda")

        # F1: 기록 저장/조회 (텍스트)
        record_fn = lambda_.Function(
            self,
            "ThimeRecordApi",
            function_name="thime-record-api",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset(os.path.join(lambda_base_path, "record_api")),
            environment=common_env,
            role=lambda_role,
            timeout=Duration.seconds(30),
            memory_size=256,
        )

        # F1: 음성 → Transcribe
        transcribe_fn = lambda_.Function(
            self,
            "ThimeTranscribeHandler",
            function_name="thime-transcribe-handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset(os.path.join(lambda_base_path, "transcribe_handler")),
            environment=common_env,
            role=lambda_role,
            timeout=Duration.seconds(60),
            memory_size=256,
        )

        # F2: Bedrock 요약·태그 추출
        bedrock_fn = lambda_.Function(
            self,
            "ThimeBedrockHandler",
            function_name="thime-bedrock-handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset(os.path.join(lambda_base_path, "bedrock_handler")),
            environment=common_env,
            role=lambda_role,
            timeout=Duration.seconds(60),
            memory_size=512,
        )

        # F3·F4: 알림 핸들러
        notification_fn = lambda_.Function(
            self,
            "ThimeNotificationHandler",
            function_name="thime-notification-handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset(os.path.join(lambda_base_path, "notification_handler")),
            environment=common_env,
            role=lambda_role,
            timeout=Duration.seconds(60),
            memory_size=256,
        )

        # F5: 다른 생각 보기
        feed_fn = lambda_.Function(
            self,
            "ThimeFeedHandler",
            function_name="thime-feed-handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset(os.path.join(lambda_base_path, "feed_handler")),
            environment=common_env,
            role=lambda_role,
            timeout=Duration.seconds(30),
            memory_size=256,
        )

        # 버블 메커니즘: 댓글 & 선택적 답장
        comment_fn = lambda_.Function(
            self,
            "ThimeCommentHandler",
            function_name="thime-comment-handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset(os.path.join(lambda_base_path, "comment_handler")),
            environment=common_env,
            role=lambda_role,
            timeout=Duration.seconds(30),
            memory_size=256,
        )

        # ─────────────────────────────────────────
        # 6. S3 이벤트 → Transcribe Lambda 트리거
        # ─────────────────────────────────────────
        audio_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(transcribe_fn),
            s3.NotificationKeyFilter(prefix="audio/", suffix=".webm"),
        )
        audio_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(transcribe_fn),
            s3.NotificationKeyFilter(prefix="audio/", suffix=".mp4"),
        )

        # ─────────────────────────────────────────
        # 7. EventBridge 스케줄 (매일 밤 10시 KST = UTC 13:00)
        # ─────────────────────────────────────────
        daily_question_rule = events.Rule(
            self,
            "ThimeDailyQuestionRule",
            rule_name="thime-daily-question",
            schedule=events.Schedule.cron(minute="0", hour="13"),  # UTC 13:00 = KST 22:00
            description="매일 밤 10시 오늘의 질문 발송 (F4)",
        )
        daily_question_rule.add_target(
            targets.LambdaFunction(
                notification_fn,
                event=events.RuleTargetInput.from_object({"source": "daily-question"}),
            )
        )

        # 매일 아침 8시 KST = UTC 23:00 (전날)
        morning_recall_rule = events.Rule(
            self,
            "ThimeMorningRecallRule",
            rule_name="thime-morning-recall",
            schedule=events.Schedule.cron(minute="0", hour="23"),  # UTC 23:00 = KST 08:00
            description="매일 아침 8시 어젯밤 기록 알림 (F3)",
        )
        morning_recall_rule.add_target(
            targets.LambdaFunction(
                notification_fn,
                event=events.RuleTargetInput.from_object({"source": "morning-recall"}),
            )
        )

        # ─────────────────────────────────────────
        # 8. API Gateway
        # ─────────────────────────────────────────
        api = apigw.RestApi(
            self,
            "ThimeApi",
            rest_api_name="thime-api",
            description="Thime Backend API",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization"],
            ),
            deploy_options=apigw.StageOptions(
                stage_name="prod",
                throttling_rate_limit=100,
                throttling_burst_limit=50,
            ),
        )

        # Cognito 인증이 필요한 메서드 옵션
        auth_method_options = apigw.MethodOptions(
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=cognito_authorizer,
        )

        # --- /records ---
        records_resource = api.root.add_resource("records")
        records_resource.add_method(
            "POST",
            apigw.LambdaIntegration(record_fn),
            method_options=auth_method_options,
        )
        records_resource.add_method(
            "GET",
            apigw.LambdaIntegration(record_fn),
            method_options=auth_method_options,
        )

        # /records/audio-url
        audio_url_resource = records_resource.add_resource("audio-url")
        audio_url_resource.add_method(
            "POST",
            apigw.LambdaIntegration(transcribe_fn),
            method_options=auth_method_options,
        )

        # /records/{id}
        record_id_resource = records_resource.add_resource("{id}")
        record_id_resource.add_method(
            "GET",
            apigw.LambdaIntegration(record_fn),
            method_options=auth_method_options,
        )
        record_id_resource.add_method(
            "DELETE",
            apigw.LambdaIntegration(record_fn),
            method_options=auth_method_options,
        )

        # /records/{id}/followup
        followup_resource = record_id_resource.add_resource("followup")
        followup_resource.add_method(
            "PATCH",
            apigw.LambdaIntegration(record_fn),
            method_options=auth_method_options,
        )

        # /records/{id}/summarize
        summarize_resource = record_id_resource.add_resource("summarize")
        summarize_resource.add_method(
            "POST",
            apigw.LambdaIntegration(bedrock_fn),
            method_options=auth_method_options,
        )

        # --- /questions ---
        questions_resource = api.root.add_resource("questions")
        today_resource = questions_resource.add_resource("today")
        today_resource.add_method(
            "GET",
            apigw.LambdaIntegration(notification_fn),
            method_options=auth_method_options,
        )

        # --- /feeds ---
        feeds_resource = api.root.add_resource("feeds")
        feed_question_resource = feeds_resource.add_resource("{questionId}")
        feed_question_resource.add_method(
            "GET",
            apigw.LambdaIntegration(feed_fn),
            method_options=auth_method_options,
        )
        feed_question_resource.add_method(
            "POST",
            apigw.LambdaIntegration(feed_fn),
            method_options=auth_method_options,
        )

        # /feeds/{questionId}/{answererUserId}/comments  (버블 메커니즘)
        feed_answerer_resource = feed_question_resource.add_resource("{answererUserId}")
        comments_resource = feed_answerer_resource.add_resource("comments")
        comments_resource.add_method(
            "POST",
            apigw.LambdaIntegration(comment_fn),
            method_options=auth_method_options,
        )
        comments_resource.add_method(
            "GET",
            apigw.LambdaIntegration(comment_fn),
            method_options=auth_method_options,
        )

        # /feeds/{questionId}/{answererUserId}/comments/{commentId}/reply
        comment_id_resource = comments_resource.add_resource("{commentId}")
        reply_resource = comment_id_resource.add_resource("reply")
        reply_resource.add_method(
            "POST",
            apigw.LambdaIntegration(comment_fn),
            method_options=auth_method_options,
        )
        reply_resource.add_method(
            "GET",
            apigw.LambdaIntegration(comment_fn),
            method_options=auth_method_options,
        )

        # ─────────────────────────────────────────
        # 9. 출력값 (배포 후 프론트엔드에서 사용)
        # ─────────────────────────────────────────
        CfnOutput(self, "UserPoolId", value=user_pool.user_pool_id, description="Cognito User Pool ID")
        CfnOutput(self, "UserPoolClientId", value=user_pool_client.user_pool_client_id, description="Cognito App Client ID")
        CfnOutput(self, "ApiUrl", value=api.url, description="API Gateway URL")
        CfnOutput(self, "AudioBucketName", value=audio_bucket.bucket_name, description="S3 Audio Bucket")
        CfnOutput(self, "CommentsTableName", value=comments_table.table_name, description="DynamoDB Comments Table")
