pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    // Poll GitHub every ~2 minutes and build automatically on new commits
    triggers {
        pollSCM('H/2 * * * *')
    }

    environment {
        IMAGE = '2025tm93214/aceest-fitness'
        SONAR_HOST_URL = 'http://localhost:9000'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Version') {
            steps {
                script {
                    env.APP_VERSION = sh(returnStdout: true,
                        script: '''grep '^DEFAULT_VERSION' app.py | cut -d'"' -f2''').trim()
                    env.IMAGE_TAG = "${env.APP_VERSION}-b${env.BUILD_NUMBER}"
                    echo "ACEest version ${env.APP_VERSION} -> image tag ${env.IMAGE_TAG}"
                }
            }
        }

        stage('Install & Lint') {
            steps {
                sh '''
                    rm -rf .venv
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                    flake8 .
                '''
            }
        }

        stage('Unit Tests & Coverage') {
            steps {
                sh '''
                    . .venv/bin/activate
                    pytest -v --junitxml=test-results.xml \
                        --cov=app --cov-report=xml --cov-report=term
                '''
            }
        }

        stage('SonarQube Analysis') {
            steps {
                withCredentials([string(credentialsId: 'sonar-token', variable: 'SONAR_TOKEN')]) {
                    sh '''
                        docker run --rm --network host \
                            --user "$(id -u):$(id -g)" \
                            -e SONAR_USER_HOME=/tmp/.sonar \
                            -e SONAR_HOST_URL="$SONAR_HOST_URL" \
                            -e SONAR_TOKEN \
                            -v "$WORKSPACE:/usr/src" \
                            sonarsource/sonar-scanner-cli \
                            -Dsonar.projectKey=aceest-fitness-gym \
                            -Dsonar.projectName="ACEest Fitness & Gym" \
                            -Dsonar.projectVersion="$APP_VERSION" \
                            -Dsonar.sources=app.py \
                            -Dsonar.tests=tests \
                            -Dsonar.python.version=3.9 \
                            -Dsonar.python.coverage.reportPaths=coverage.xml \
                            -Dsonar.qualitygate.wait=true
                    '''
                }
            }
        }

        stage('Docker Build & Container Tests') {
            steps {
                sh '''
                    docker build -t ${IMAGE}:${IMAGE_TAG} .
                    docker run --rm ${IMAGE}:${IMAGE_TAG} pytest -q
                '''
            }
        }

        stage('Push to Docker Hub') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub-creds',
                        usernameVariable: 'DH_USER', passwordVariable: 'DH_PASS')]) {
                    sh '''
                        echo "$DH_PASS" | docker login -u "$DH_USER" --password-stdin
                        docker push ${IMAGE}:${IMAGE_TAG}
                        docker logout
                    '''
                }
            }
        }

        stage('Archive Artifacts') {
            steps {
                sh 'echo "${IMAGE}:${IMAGE_TAG}" > build-info.txt'
                archiveArtifacts artifacts: 'build-info.txt,coverage.xml,test-results.xml', fingerprint: true
            }
        }
    }

    post {
        always {
            junit allowEmptyResults: true, testResults: 'test-results.xml'
            sh 'rm -rf .venv .scannerwork || true'
        }
        success { echo "BUILD SUCCESS - ${env.IMAGE}:${env.IMAGE_TAG} published." }
        failure { echo 'BUILD FAILED - check the stage logs above.' }
    }
}
