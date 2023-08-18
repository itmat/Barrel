from barrel.configuration import Analysis, Infrastructure

infrastructure = Infrastructure()

analyses = {
    "analysis": Analysis(
        infrastructure=infrastructure,
    )
}
