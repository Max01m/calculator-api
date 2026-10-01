// Jenkinsfile
//
// Пайплайн для calculator-api: 
//   1. Checkout — забирает код
//   2. Test — прогоняет юнит-тесты
//   3. Determine next version — вычисляет новую версию (semantic versioning
//      по Conventional Commits, см. scripts/bump_version.sh)
//   4. Commit & tag version — коммитит VERSION и ставит git-тег, пушит в GitHub
//   5. Build image — собирает локальный Docker-образ с новой версией
//
// Требуемые credentials в Jenkins (Manage Jenkins -> Credentials):
//   - "git-push-credentials" — GitHub Personal Access Token с правом push в репозиторий
//     (логин: ваш GitHub-логин, пароль: сам токен, тип credential: Username with password)

pipeline {
    agent any

    options {
        skipDefaultCheckout(false)
        disableConcurrentBuilds()
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Test') {
    steps {
        sh """
            docker run --rm --volumes-from jenkins -w ${WORKSPACE} python:3.12-slim \
                bash -c "pip install --no-cache-dir -r requirements.txt pytest httpx && python -m pytest tests/ -v"
        """
    }
}

        stage('Determine next version') {
            when { branch 'main' }
            steps {
                script {
                    sh 'chmod +x scripts/bump_version.sh'
                    env.NEW_VERSION = sh(
                        script: "bash scripts/bump_version.sh | tail -n1",
                        returnStdout: true
                    ).trim()
                    echo "Новая версия калькулятора: ${env.NEW_VERSION}"
                }
            }
        }

        stage('Commit & tag version') {
            when { branch 'main' }
            steps {
                withCredentials([usernamePassword(credentialsId: 'git-push-credentials',
                                                   usernameVariable: 'GIT_USER',
                                                   passwordVariable: 'GIT_TOKEN')]) {
                    sh '''
                        git config user.email "ci@jenkins.local"
                        git config user.name "Jenkins CI"
                        git remote set-url origin https://${GIT_USER}:${GIT_TOKEN}@$(git remote get-url origin | sed -E 's#https?://##')
                        git add VERSION
                        git commit -m "chore(release): bump version to ${NEW_VERSION} [skip ci]" || echo "Нет изменений"
                        git tag "v${NEW_VERSION}"
                        git push origin HEAD:main
                        git push origin "v${NEW_VERSION}"
                    '''
                }
            }
        }

        stage('Build image') {
            when { branch 'main' }
            steps {
                sh """
                    docker build --build-arg APP_VERSION=${NEW_VERSION} \
                        -t calculator-api:${NEW_VERSION} \
                        -t calculator-api:latest .
                """
            }
        }
    }

    post {
        success {
            echo "Пайплайн завершён успешно. Версия: ${env.NEW_VERSION ?: 'н/д (не main)'}. Локальный образ: calculator-api:${env.NEW_VERSION ?: 'latest'}"
        }
        failure {
            echo "Пайплайн завершился с ошибкой — версия НЕ обновлена, образ НЕ собран."
        }
    }
}

// ------------------------------------------------------------------------
// позже если появится реестр образов или сервер для деплоя, нужно добавить
// такие стадии после 'Build image' (нужны доп. credentials
// "docker-registry-creds" и "deploy-ssh-key"):
//
// stage('Push image') {
//     steps {
//         withCredentials([usernamePassword(credentialsId: 'docker-registry-creds',
//                                            usernameVariable: 'REG_USER',
//                                            passwordVariable: 'REG_PASS')]) {
//             sh """
//                 echo "\$REG_PASS" | docker login -u "\$REG_USER" --password-stdin
//                 docker tag calculator-api:${NEW_VERSION} <ваш_логин>/calculator-api:${NEW_VERSION}
//                 docker push <ваш_логин>/calculator-api:${NEW_VERSION}
//             """
//         }
//     }
// }
//
// stage('Deploy') {
//     steps {
//         sshagent(credentials: ['deploy-ssh-key']) {
//             sh "ssh user@server 'docker pull ... && docker run ...'"
//         }
//     }
// }
