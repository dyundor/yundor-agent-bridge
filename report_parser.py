def extract_text(result):

    output = []


    for part in result.get(
        "parts",
        []
    ):

        if part.get("type") == "text":

            output.append(
                part["text"]
            )


    return "\n".join(output)