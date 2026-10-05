pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 15, unit: 'MINUTES')
    }

    stages {
        stage('Checkout') {
            steps {
                // Pulls the latest code from GitHub (configured in the job's SCM settings)
                checkout scm
            }
        }

        stage('Clean Build Environment') {
            steps {
                sh '''
                    rm -rf .venv
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Lint') {
            steps {
                sh '. .venv/bin/activate && flake8 .'
            }
        }

        stage('Unit Tests') {
            steps {
                sh '. .venv/bin/activate && pytest -v'
            }
        }

        stage('Docker Build') {
            steps {
                sh '''
                    if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
                        docker build -t aceest-fitness:${BUILD_NUMBER} .
                    else
                        echo "Docker not accessible to Jenkins - skipping image build (verified in GitHub Actions)"
                    fi
                '''
            }
        }
    }

    post {
        success { echo 'BUILD SUCCESS - ACEest pipeline passed.' }
        failure { echo 'BUILD FAILED - check the stage logs above.' }
        cleanup { sh 'rm -rf .venv' }
    }
}
